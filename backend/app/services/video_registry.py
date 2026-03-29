from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
from threading import RLock
from threading import Thread
from typing import Literal
from uuid import uuid4

from backend.app.config import get_settings
from backend.app.integrations.gemini_client import GeminiVideoSource
from backend.app.schemas.analytics import MatchAnalyticsSummary
from backend.app.schemas.common import (
    ProcessingStage,
    RulesetVariant,
    VideoAssetStatus,
    VideoSourceType,
)
from backend.app.schemas.preprocessing import CandidateClip
from backend.app.schemas.processing_job import ProcessingJob
from backend.app.schemas.set_event import SetEvent
from backend.app.schemas.video_asset import VideoAsset
from backend.app.schemas.video_ingest import AssetPlaceholder, VideoJobSummary
from backend.app.services.analyze_candidate_clips import analyze_candidate_clips_to_events
from backend.app.services.analytics_aggregation import summarize_set_events


class VideoSubmissionError(ValueError):
    pass


logger = logging.getLogger("volleyball_ai.video_registry")


@dataclass(slots=True)
class VideoIngestionRecord:
    video_asset: VideoAsset
    processing_job: ProcessingJob
    title: str
    source_file_name: str | None
    normalized_asset: AssetPlaceholder
    proxy_asset: AssetPlaceholder
    message: str
    candidate_clips: list[CandidateClip]
    set_events: list[SetEvent]
    analytics_summary: MatchAnalyticsSummary | None


class InMemoryVideoRegistry:
    def __init__(self) -> None:
        self._records: dict[str, VideoIngestionRecord] = {}
        self._lock = RLock()

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def create_video(
        self,
        *,
        title: str | None,
        source_type: VideoSourceType,
        ruleset_variant: RulesetVariant,
        source_url: str | None = None,
        local_path: str | None = None,
        source_file_name: str | None = None,
        source_file_bytes: bytes | None = None,
        source_mime_type: str | None = None,
        duration_seconds: float | None = None,
        fps: float | None = None,
    ) -> VideoJobSummary:
        self._validate_submission(
            source_type=source_type,
            source_url=source_url,
            local_path=local_path,
            source_file_name=source_file_name,
            source_file_bytes=source_file_bytes,
        )

        with self._lock:
            created_at = datetime.now(tz=timezone.utc)
            updated_at = created_at
            video_asset_id = f"video-{uuid4().hex[:12]}"
            job_id = f"job-{uuid4().hex[:12]}"
            resolved_title = self._resolve_title(
                title=title,
                source_type=source_type,
                source_file_name=source_file_name,
                local_path=local_path,
                source_url=source_url,
            )
            resolved_local_path = self._resolve_local_path(
                source_type=source_type,
                local_path=local_path,
            )
            stored_local_path = self._store_source_file(
                video_asset_id=video_asset_id,
                source_file_name=source_file_name,
                source_file_bytes=source_file_bytes,
            )
            effective_local_path = resolved_local_path or stored_local_path
            message = self._build_message(source_type=source_type)

            video_asset = VideoAsset(
                video_asset_id=video_asset_id,
                source_type=source_type,
                source_url=source_url,
                local_path=effective_local_path,
                mime_type=source_mime_type,
                duration_seconds=duration_seconds,
                fps=fps,
                ruleset_variant=ruleset_variant,
                status=VideoAssetStatus.uploaded,
                created_at=created_at,
                updated_at=updated_at,
            )
            processing_job = ProcessingJob(
                job_id=job_id,
                video_asset_id=video_asset_id,
                stage=ProcessingStage.queued,
                progress=0.0,
                created_at=created_at,
                updated_at=updated_at,
                error_message=None,
            )
            normalized_asset = self._build_placeholder(
                video_asset_id=video_asset_id,
                kind="normalized",
                duration_seconds=duration_seconds,
                fps=fps,
            )
            proxy_asset = self._build_placeholder(
                video_asset_id=video_asset_id,
                kind="proxy",
                duration_seconds=duration_seconds,
                fps=fps,
            )

            record = VideoIngestionRecord(
                video_asset=video_asset,
                processing_job=processing_job,
                title=resolved_title,
                source_file_name=source_file_name,
                normalized_asset=normalized_asset,
                proxy_asset=proxy_asset,
                message=message,
                candidate_clips=[],
                set_events=[],
                analytics_summary=None,
            )
            self._records[video_asset_id] = record
            logger.info(
                "Video record created | video_id=%s | job_id=%s | source_type=%s | ruleset=%s | local_path=%s",
                video_asset_id,
                job_id,
                source_type,
                ruleset_variant,
                effective_local_path,
            )
            return self._to_summary(record)

    def get_video(self, video_asset_id: str) -> VideoJobSummary | None:
        with self._lock:
            record = self._records.get(video_asset_id)
            if record is None:
                return None
            return self._to_summary(record)

    def get_events(self, video_asset_id: str) -> list[SetEvent] | None:
        with self._lock:
            record = self._records.get(video_asset_id)
            if record is None:
                return None
            return list(record.set_events)

    def get_analytics(self, video_asset_id: str) -> MatchAnalyticsSummary | None:
        with self._lock:
            record = self._records.get(video_asset_id)
            if record is None:
                return None
            return record.analytics_summary

    def start_processing(self, video_asset_id: str) -> None:
        with self._lock:
            record = self._records.get(video_asset_id)
            if record is None:
                raise VideoSubmissionError("Video not found.")
            if record.processing_job.stage == ProcessingStage.running:
                logger.info(
                    "Background processing already running | video_id=%s | stage=%s",
                    video_asset_id,
                    record.processing_job.stage,
                )
                return
            logger.info(
                "Starting background processing | video_id=%s | current_stage=%s",
                video_asset_id,
                record.processing_job.stage,
            )
        thread = Thread(
            target=self._process_video,
            args=(video_asset_id,),
            daemon=True,
            name=f"video-processing-{video_asset_id}",
        )
        thread.start()
        logger.info(
            "Background thread started | video_id=%s | thread_name=%s",
            video_asset_id,
            thread.name,
        )

    def _validate_submission(
        self,
        *,
        source_type: VideoSourceType,
        source_url: str | None,
        local_path: str | None,
        source_file_name: str | None,
        source_file_bytes: bytes | None,
    ) -> None:
        if source_type == VideoSourceType.youtube and not source_url:
            raise VideoSubmissionError("sourceUrl is required when sourceType is youtube.")

        if source_type == VideoSourceType.local_path:
            if not local_path:
                raise VideoSubmissionError("localPath is required when sourceType is local_path.")
            candidate_path = Path(local_path).expanduser()
            if not candidate_path.exists():
                raise VideoSubmissionError(f"localPath does not exist: {candidate_path}")
            if not candidate_path.is_file():
                raise VideoSubmissionError(f"localPath must be a file: {candidate_path}")

        if source_type == VideoSourceType.upload:
            if not source_file_name:
                raise VideoSubmissionError("file is required when sourceType is upload.")
            if source_file_bytes in (None, b""):
                raise VideoSubmissionError(
                    "uploaded file bytes are required when sourceType is upload."
                )

    def _resolve_title(
        self,
        *,
        title: str | None,
        source_type: VideoSourceType,
        source_file_name: str | None,
        local_path: str | None,
        source_url: str | None,
    ) -> str:
        normalized = (title or "").strip()
        if normalized:
            return normalized

        if source_type == VideoSourceType.local_path and local_path:
            return Path(local_path).stem.replace("_", " ").strip() or "Local match"

        if source_file_name:
            return Path(source_file_name).stem.replace("_", " ").strip() or "Uploaded match"

        if source_type == VideoSourceType.youtube and source_url:
            return "YouTube match"

        return "Volleyball match"

    def _build_message(self, *, source_type: VideoSourceType) -> str:
        if source_type == VideoSourceType.youtube:
            return "Queued YouTube video for normalization."
        if source_type == VideoSourceType.local_path:
            return "Queued local video path for analysis."
        return "Queued uploaded video for normalization."

    def _process_video(self, video_asset_id: str) -> None:
        try:
            logger.info("Processing started | video_id=%s", video_asset_id)
            self._update_job(
                video_asset_id,
                stage=ProcessingStage.running,
                progress=0.1,
                message="Preparing clip for analysis.",
            )
            candidate_clips = [self._build_whole_video_candidate_clip(video_asset_id)]
            self._set_candidate_clips(video_asset_id, candidate_clips)
            logger.info(
                "Candidate clips prepared | video_id=%s | clip_count=%s | clip_ids=%s",
                video_asset_id,
                len(candidate_clips),
                [clip.candidate_clip_id for clip in candidate_clips],
            )
            self._update_job(
                video_asset_id,
                stage=ProcessingStage.running,
                progress=0.45,
                message="Analyzing clip with Gemini.",
            )
            video_source = self._build_video_source(video_asset_id)
            logger.info(
                "Gemini analysis starting | video_id=%s | source_type=%s | uri=%s | mime_type=%s",
                video_asset_id,
                video_source.source_type,
                video_source.uri,
                video_source.mime_type,
            )
            result = analyze_candidate_clips_to_events(
                video_asset_id=video_asset_id,
                candidate_clips=candidate_clips,
                video_source=video_source,
            )
            logger.info(
                "Gemini analysis completed | video_id=%s | returned_events=%s",
                video_asset_id,
                len(result.set_events),
            )
            self._update_job(
                video_asset_id,
                stage=ProcessingStage.running,
                progress=0.8,
                message="Computing setter analytics.",
            )
            self._set_results(
                video_asset_id=video_asset_id,
                set_events=result.set_events,
            )
            analytics = self.get_analytics(video_asset_id)
            logger.info(
                "Analytics computed | video_id=%s | total_events=%s | overall_total_sets=%s",
                video_asset_id,
                len(result.set_events),
                analytics.overall.total_set_attempts if analytics is not None else 0,
            )
            final_message = (
                "Analysis completed."
                if result.set_events
                else "Analysis completed with no set events detected."
            )
            self._update_job(
                video_asset_id,
                stage=ProcessingStage.completed,
                progress=1.0,
                message=final_message,
            )
            logger.info("Processing completed | video_id=%s | message=%s", video_asset_id, final_message)
        except Exception as exc:
            logger.exception("Processing failed | video_id=%s", video_asset_id)
            self._update_job(
                video_asset_id,
                stage=ProcessingStage.failed,
                progress=1.0,
                message=f"Analysis failed: {exc}",
                error_message=str(exc),
            )

    def _build_whole_video_candidate_clip(self, video_asset_id: str) -> CandidateClip:
        return CandidateClip(
            candidate_clip_id=f"{video_asset_id}-whole-video",
            video_asset_id=video_asset_id,
            rally_segment_id=None,
            start_time_s=0.0,
            end_time_s=1.0,
            trigger_label="whole_video",
            confidence=0.95,
        )

    def _build_video_source(self, video_asset_id: str) -> GeminiVideoSource:
        with self._lock:
            record = self._records[video_asset_id]
            asset = record.video_asset
        if asset.source_type == VideoSourceType.youtube and asset.source_url:
            return GeminiVideoSource(
                source_type=asset.source_type,
                uri=asset.source_url,
                mime_type=asset.mime_type or "video/mp4",
            )
        if asset.local_path:
            return GeminiVideoSource(
                source_type=asset.source_type,
                uri=asset.local_path,
                mime_type=asset.mime_type or "video/mp4",
            )
        raise VideoSubmissionError("No usable video source available for analysis.")

    def _resolve_local_path(
        self,
        *,
        source_type: VideoSourceType,
        local_path: str | None,
    ) -> str | None:
        if source_type != VideoSourceType.local_path or not local_path:
            return None

        return str(Path(local_path).expanduser().resolve())

    def _set_candidate_clips(
        self,
        video_asset_id: str,
        candidate_clips: list[CandidateClip],
    ) -> None:
        with self._lock:
            self._records[video_asset_id].candidate_clips = list(candidate_clips)

    def _set_results(
        self,
        *,
        video_asset_id: str,
        set_events: list[SetEvent],
    ) -> None:
        with self._lock:
            record = self._records[video_asset_id]
            record.set_events = list(set_events)
            record.analytics_summary = summarize_set_events(
                video_asset_id=video_asset_id,
                ruleset_variant=record.video_asset.ruleset_variant,
                set_events=record.set_events,
            )

    def _update_job(
        self,
        video_asset_id: str,
        *,
        stage: ProcessingStage,
        progress: float,
        message: str,
        error_message: str | None = None,
    ) -> None:
        with self._lock:
            record = self._records[video_asset_id]
            previous_stage = record.processing_job.stage
            previous_progress = record.processing_job.progress
            record.processing_job.stage = stage
            record.processing_job.progress = progress
            record.processing_job.error_message = error_message
            record.processing_job.updated_at = datetime.now(tz=timezone.utc)
            record.message = message
            logger.info(
                "Job updated | video_id=%s | stage=%s->%s | progress=%.2f->%.2f | message=%s | error=%s",
                video_asset_id,
                previous_stage,
                stage,
                previous_progress,
                progress,
                message,
                error_message,
            )

    def _store_source_file(
        self,
        *,
        video_asset_id: str,
        source_file_name: str | None,
        source_file_bytes: bytes | None,
    ) -> str | None:
        if not source_file_name or source_file_bytes is None:
            return None

        settings = get_settings()
        safe_name = Path(source_file_name).name or "uploaded-video.mp4"
        source_dir = Path(settings.storage_root) / video_asset_id / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        destination = source_dir / safe_name
        destination.write_bytes(source_file_bytes)
        logger.info(
            "Stored uploaded file | video_id=%s | path=%s | bytes=%s",
            video_asset_id,
            destination,
            len(source_file_bytes),
        )
        return str(destination)

    def _build_placeholder(
        self,
        *,
        video_asset_id: str,
        kind: Literal["normalized", "proxy"],
        duration_seconds: float | None,
        fps: float | None,
    ) -> AssetPlaceholder:
        asset_root = Path("/tmp/volleyball_ai") / video_asset_id
        return AssetPlaceholder(
            kind=kind,
            path=str(asset_root / f"{kind}.mp4"),
            status=VideoAssetStatus.normalizing,
            format="mp4",
            codec="h264",
            duration_seconds=duration_seconds,
            fps=fps,
        )

    def _to_summary(self, record: VideoIngestionRecord) -> VideoJobSummary:
        return VideoJobSummary(
            id=record.video_asset.video_asset_id,
            job_id=record.processing_job.job_id,
            title=record.title,
            source_type=record.video_asset.source_type,
            source_url=record.video_asset.source_url,
            local_path=record.video_asset.local_path,
            mime_type=record.video_asset.mime_type,
            source_file_name=record.source_file_name,
            ruleset_variant=record.video_asset.ruleset_variant,
            status=record.processing_job.stage,
            progress=record.processing_job.progress,
            message=record.message,
            normalized_asset=record.normalized_asset,
            proxy_asset=record.proxy_asset,
            created_at=record.processing_job.created_at,
            updated_at=record.processing_job.updated_at,
        )


_REGISTRY = InMemoryVideoRegistry()


def get_video_registry() -> InMemoryVideoRegistry:
    return _REGISTRY
