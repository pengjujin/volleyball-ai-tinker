from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.app.config import get_settings
from backend.app.schemas.common import SetTempo, TeamSide, VideoSourceType
from backend.app.schemas.gemini_analysis import CourtPoint, GeminiSetAnalysis
from backend.app.schemas.preprocessing import CandidateClip

try:  # pragma: no cover - import availability depends on installed SDK.
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - handled at runtime when live mode is requested.
    genai = None
    types = None


class GeminiResponseValidationError(ValueError):
    pass


class GeminiClientError(RuntimeError):
    pass


logger = logging.getLogger("volleyball_ai.gemini")


@dataclass(frozen=True, slots=True)
class GeminiVideoSource:
    source_type: VideoSourceType
    uri: str
    mime_type: str = "video/mp4"


class _CourtPointPayload(BaseModel):
    x: float
    y: float

    model_config = ConfigDict(extra="forbid")


class _GeminiResponsePayload(BaseModel):
    candidate_clip_id: str
    contains_set: bool
    setter_team_side: TeamSide = TeamSide.unknown
    contact_time_s: float | None = Field(default=None, ge=0.0)
    target_zone: str | None = None
    set_type: str | None = None
    set_success: bool | None = None
    success_reason: str | None = None
    set_tempo: SetTempo | None = None
    setter_court_position: _CourtPointPayload | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_set_specific_fields(self) -> _GeminiResponsePayload:
        if self.contains_set:
            missing: list[str] = []
            if self.contact_time_s is None:
                missing.append("contact_time_s")
            if self.target_zone is None:
                missing.append("target_zone")
            if self.set_success is None:
                missing.append("set_success")
            if self.set_tempo is None:
                missing.append("set_tempo")
            if missing:
                missing_text = ", ".join(missing)
                raise ValueError(
                    f"contains_set=True requires {missing_text} to be provided."
                )

        return self


@dataclass(frozen=True, slots=True)
class GeminiClientConfig:
    minimum_stub_confidence: float = 0.55
    model_name: str = "gemini-2.5-pro"
    video_fps: float = 2.0
    inline_video_max_bytes: int = 20 * 1024 * 1024
    file_poll_interval_s: float = 2.0
    file_ready_timeout_s: float = 120.0
    prefer_files_api_for_videos: bool = True


@dataclass(slots=True)
class _UploadedFileReference:
    file_uri: str
    mime_type: str | None


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        response_provider: Callable[[CandidateClip], Mapping[str, Any] | GeminiSetAnalysis | None]
        | None = None,
        config: GeminiClientConfig | None = None,
    ) -> None:
        settings = get_settings()
        self._response_provider = response_provider
        self._config = config or GeminiClientConfig(
            model_name=settings.gemini_model,
            video_fps=settings.gemini_video_fps,
            inline_video_max_bytes=settings.gemini_inline_video_max_bytes,
        )
        self._api_key = api_key or settings.gemini_api_key
        self._live_enabled = settings.gemini_live_enabled
        self._live_client = None
        self._uploaded_files: dict[str, _UploadedFileReference] = {}

    def analyze_candidate_clip(
        self,
        candidate_clip: CandidateClip,
        *,
        raw_response: Mapping[str, Any] | GeminiSetAnalysis | None = None,
        video_source: GeminiVideoSource | None = None,
    ) -> GeminiSetAnalysis:
        response = raw_response
        if response is None and self._response_provider is not None:
            logger.info(
                "Gemini response provider used | candidate_clip_id=%s",
                candidate_clip.candidate_clip_id,
            )
            response = self._response_provider(candidate_clip)
        if response is None and video_source is not None and self._api_key and self._live_enabled:
            logger.info(
                "Gemini live analysis enabled | candidate_clip_id=%s | source_type=%s | uri=%s",
                candidate_clip.candidate_clip_id,
                video_source.source_type,
                video_source.uri,
            )
            response = self._build_live_response(candidate_clip, video_source)
        if response is None:
            logger.info(
                "Gemini stub response used | candidate_clip_id=%s | live_enabled=%s | has_api_key=%s",
                candidate_clip.candidate_clip_id,
                self._live_enabled,
                bool(self._api_key),
            )
            response = self._build_stub_response(candidate_clip)

        return self._parse_response(candidate_clip.candidate_clip_id, response)

    def _build_live_response(
        self,
        candidate_clip: CandidateClip,
        video_source: GeminiVideoSource,
    ) -> Mapping[str, Any]:
        if genai is None or types is None:
            raise GeminiClientError(
                "google-genai is not installed; cannot run live Gemini analysis."
            )

        try:
            logger.info(
                "Sending Gemini request | candidate_clip_id=%s | model=%s",
                candidate_clip.candidate_clip_id,
                self._config.model_name,
            )
            client = self._get_live_client()
            response = client.models.generate_content(
                model=self._config.model_name,
                contents=[
                    self._build_video_part(candidate_clip, video_source),
                    self._build_prompt(candidate_clip),
                ],
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": GeminiSetAnalysis.model_json_schema(),
                },
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent.
            raise GeminiClientError(f"Gemini request failed: {exc}") from exc

        response_text = getattr(response, "text", None)
        if not response_text:
            raise GeminiClientError("Gemini response did not include text output.")
        logger.info(
            "Gemini response received | candidate_clip_id=%s | text_length=%s",
            candidate_clip.candidate_clip_id,
            len(response_text),
        )

        try:
            return GeminiSetAnalysis.model_validate_json(response_text).model_dump()
        except ValidationError as exc:
            raise GeminiResponseValidationError(str(exc)) from exc

    def _get_live_client(self):
        if self._live_client is None:
            if not self._api_key:
                raise GeminiClientError("GEMINI_API_KEY is not configured.")
            logger.info("Creating Gemini SDK client")
            self._live_client = genai.Client(api_key=self._api_key)
        return self._live_client

    def _build_video_part(self, candidate_clip: CandidateClip, video_source: GeminiVideoSource):
        video_metadata = None
        if candidate_clip.trigger_label != "whole_video":
            video_metadata = types.VideoMetadata(
                start_offset=f"{candidate_clip.start_time_s}s",
                end_offset=f"{candidate_clip.end_time_s}s",
                fps=self._config.video_fps,
            )

        if video_source.source_type == VideoSourceType.youtube:
            logger.info(
                "Preparing Gemini video part from YouTube URL | candidate_clip_id=%s",
                candidate_clip.candidate_clip_id,
            )
            part_kwargs = {"file_data": types.FileData(file_uri=video_source.uri)}
            if video_metadata is not None:
                part_kwargs["video_metadata"] = video_metadata
            return types.Part(**part_kwargs)

        local_path = Path(video_source.uri)
        if not local_path.exists():
            raise GeminiClientError(f"Local video path does not exist: {local_path}")

        if (
            not self._config.prefer_files_api_for_videos
            and local_path.stat().st_size <= self._config.inline_video_max_bytes
        ):
            logger.info(
                "Preparing inline Gemini video bytes | candidate_clip_id=%s | path=%s | bytes=%s",
                candidate_clip.candidate_clip_id,
                local_path,
                local_path.stat().st_size,
            )
            part_kwargs = {
                "inline_data": types.Blob(
                    data=local_path.read_bytes(),
                    mime_type=video_source.mime_type,
                )
            }
            if video_metadata is not None:
                part_kwargs["video_metadata"] = video_metadata
            return types.Part(**part_kwargs)

        uploaded_reference = self._uploaded_files.get(str(local_path))
        if uploaded_reference is None:
            logger.info(
                "Uploading local video to Gemini Files API | candidate_clip_id=%s | path=%s",
                candidate_clip.candidate_clip_id,
                local_path,
            )
            uploaded = self._get_live_client().files.upload(file=str(local_path))
            uploaded = self._wait_for_file_active(uploaded, candidate_clip.candidate_clip_id)
            uploaded_reference = _UploadedFileReference(
                file_uri=uploaded.uri,
                mime_type=getattr(uploaded, "mime_type", video_source.mime_type),
            )
            self._uploaded_files[str(local_path)] = uploaded_reference
        else:
            logger.info(
                "Reusing uploaded Gemini file reference | candidate_clip_id=%s | path=%s",
                candidate_clip.candidate_clip_id,
                local_path,
            )

        part_kwargs = {
            "file_data": types.FileData(
                file_uri=uploaded_reference.file_uri,
                mime_type=uploaded_reference.mime_type,
            )
        }
        if video_metadata is not None:
            part_kwargs["video_metadata"] = video_metadata
        return types.Part(**part_kwargs)

    def _wait_for_file_active(self, uploaded_file: Any, candidate_clip_id: str) -> Any:
        file_name = getattr(uploaded_file, "name", None)
        if not file_name:
            raise GeminiClientError(
                "Gemini uploaded file response did not include a file name."
            )

        deadline = time.monotonic() + self._config.file_ready_timeout_s
        current_file = uploaded_file

        while True:
            state_name = _extract_file_state_name(current_file)
            if state_name == "ACTIVE":
                logger.info(
                    "Gemini uploaded file is ACTIVE | candidate_clip_id=%s | file_name=%s",
                    candidate_clip_id,
                    file_name,
                )
                return current_file

            if state_name in {"FAILED", "CANCELLED"}:
                raise GeminiClientError(
                    f"Gemini uploaded file entered terminal state {state_name} before becoming ACTIVE."
                )

            if time.monotonic() >= deadline:
                raise GeminiClientError(
                    f"Timed out waiting for Gemini uploaded file {file_name} to become ACTIVE; last_state={state_name or 'unknown'}."
                )

            logger.info(
                "Waiting for Gemini uploaded file to become ACTIVE | candidate_clip_id=%s | file_name=%s | state=%s",
                candidate_clip_id,
                file_name,
                state_name or "unknown",
            )
            time.sleep(self._config.file_poll_interval_s)
            current_file = self._get_live_client().files.get(name=file_name)

    def _build_prompt(self, candidate_clip: CandidateClip) -> str:
        return (
            "Analyze this volleyball video clip for setter action only. "
            "Return structured JSON that matches the schema exactly. "
            "A successful set means the ball is attackable for a teammate. "
            "Use tempo buckets quick, medium, or high/slow. "
            f"The candidate clip id is {candidate_clip.candidate_clip_id}. "
            "If there is no set in this clip, set contains_set to false."
        )

    def _parse_response(
        self,
        candidate_clip_id: str,
        response: Mapping[str, Any] | GeminiSetAnalysis,
    ) -> GeminiSetAnalysis:
        if isinstance(response, GeminiSetAnalysis):
            if response.candidate_clip_id != candidate_clip_id:
                raise GeminiResponseValidationError(
                    "candidate_clip_id does not match the analyzed clip."
                )
            return response

        try:
            payload = _GeminiResponsePayload.model_validate(response)
        except ValidationError as exc:  # pragma: no cover - exercised through tests
            raise GeminiResponseValidationError(str(exc)) from exc

        if payload.candidate_clip_id != candidate_clip_id:
            raise GeminiResponseValidationError(
                "candidate_clip_id does not match the analyzed clip."
            )

        return GeminiSetAnalysis(
            candidate_clip_id=payload.candidate_clip_id,
            contains_set=payload.contains_set,
            setter_team_side=payload.setter_team_side,
            contact_time_s=payload.contact_time_s,
            target_zone=payload.target_zone,
            set_type=payload.set_type,
            set_success=payload.set_success,
            success_reason=payload.success_reason,
            set_tempo=payload.set_tempo,
            setter_court_position=(
                CourtPoint(
                    x=payload.setter_court_position.x,
                    y=payload.setter_court_position.y,
                )
                if payload.setter_court_position is not None
                else None
            ),
            confidence=payload.confidence,
            notes=payload.notes,
        )

    def _build_stub_response(self, candidate_clip: CandidateClip) -> dict[str, Any]:
        contains_set = (
            candidate_clip.confidence >= self._config.minimum_stub_confidence
            or candidate_clip.trigger_label in {"ball_motion_peak", "audio_contact_burst"}
        )
        setter_team_side = (
            TeamSide.near_side
            if int(candidate_clip.start_time_s * 10) % 2 == 0
            else TeamSide.far_side
        )
        set_tempo = _tempo_from_confidence(candidate_clip.confidence)
        confidence = min(
            1.0,
            max(
                candidate_clip.confidence,
                0.35 if not contains_set else 0.55,
            ),
        )

        payload: dict[str, Any] = {
            "candidate_clip_id": candidate_clip.candidate_clip_id,
            "contains_set": contains_set,
            "setter_team_side": setter_team_side,
            "confidence": round(confidence, 3),
            "notes": "stubbed Gemini analysis",
        }

        if contains_set:
            payload.update(
                {
                    "contact_time_s": round(
                        candidate_clip.start_time_s
                        + (candidate_clip.end_time_s - candidate_clip.start_time_s) / 2,
                        3,
                    ),
                    "target_zone": _target_zone_from_candidate(candidate_clip),
                    "set_type": _set_type_from_candidate(candidate_clip),
                    "set_success": candidate_clip.confidence >= 0.68,
                    "success_reason": (
                        "attackable_ball"
                        if candidate_clip.confidence >= 0.68
                        else "candidate_clip_requires_follow_up"
                    ),
                    "set_tempo": set_tempo,
                    "setter_court_position": {
                        "x": round(4.0 + ((candidate_clip.start_time_s * 1.3) % 2.0), 3),
                        "y": round(2.0 + ((candidate_clip.end_time_s * 0.9) % 3.0), 3),
                    },
                }
            )
        else:
            payload.update(
                {
                    "set_success": False,
                    "set_tempo": set_tempo,
                }
            )

        return payload


def _tempo_from_confidence(confidence: float) -> SetTempo:
    if confidence >= 0.75:
        return SetTempo.quick
    if confidence >= 0.55:
        return SetTempo.medium
    return SetTempo.high_slow


def _target_zone_from_candidate(candidate_clip: CandidateClip) -> str:
    if candidate_clip.start_time_s % 3 < 1:
        return "zone_4"
    if candidate_clip.start_time_s % 3 < 2:
        return "zone_2"
    return "zone_3"


def _set_type_from_candidate(candidate_clip: CandidateClip) -> str:
    if candidate_clip.trigger_label == "audio_contact_burst":
        return "tempo"
    if candidate_clip.trigger_label == "ball_motion_peak":
        return "outside"
    return "transition"


def _extract_file_state_name(uploaded_file: Any) -> str | None:
    state = getattr(uploaded_file, "state", None)
    if state is None:
        return None

    state_name = getattr(state, "name", None)
    if state_name is not None:
        return str(state_name)

    return str(state)
