from __future__ import annotations

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from backend.app.schemas.gemini_analysis import GeminiSetAnalysis
from backend.app.schemas.set_event import SetEvent


def normalize_gemini_set_analysis(
    analysis: GeminiSetAnalysis,
    *,
    video_asset_id: str,
    rally_segment_id: str | None = None,
    created_at: datetime | None = None,
) -> SetEvent | None:
    if not analysis.contains_set:
        return None

    if analysis.contact_time_s is None:
        return None

    if analysis.target_zone is None or not analysis.target_zone.strip():
        return None

    if analysis.set_success is None or analysis.set_tempo is None:
        return None

    timestamp_s = round(float(analysis.contact_time_s), 3)
    target_zone = analysis.target_zone.strip()
    event_id = _build_event_id(
        video_asset_id=video_asset_id,
        candidate_clip_id=analysis.candidate_clip_id,
        rally_segment_id=rally_segment_id,
        timestamp_s=timestamp_s,
        setter_team_side=analysis.setter_team_side.value,
        target_zone=target_zone,
        set_type=analysis.set_type,
        set_success=analysis.set_success,
        set_tempo=analysis.set_tempo.value,
    )
    court_position = analysis.setter_court_position

    return SetEvent(
        set_event_id=event_id,
        video_asset_id=video_asset_id,
        rally_segment_id=rally_segment_id,
        source_candidate_clip_id=analysis.candidate_clip_id,
        timestamp_s=timestamp_s,
        setter_team_side=analysis.setter_team_side,
        target_zone=target_zone,
        set_type=_clean_text(analysis.set_type),
        set_success=analysis.set_success,
        success_reason=_clean_text(analysis.success_reason),
        set_tempo=analysis.set_tempo,
        setter_court_x=court_position.x if court_position is not None else None,
        setter_court_y=court_position.y if court_position is not None else None,
        confidence=round(float(analysis.confidence), 4),
        notes=_clean_text(analysis.notes),
        created_at=created_at or datetime.now(tz=timezone.utc),
    )


def normalize_gemini_set_analyses(
    analyses: list[GeminiSetAnalysis],
    *,
    video_asset_id: str,
    rally_segment_id: str | None = None,
    created_at: datetime | None = None,
) -> list[SetEvent]:
    normalized: list[SetEvent] = []
    for analysis in analyses:
        event = normalize_gemini_set_analysis(
            analysis,
            video_asset_id=video_asset_id,
            rally_segment_id=rally_segment_id,
            created_at=created_at,
        )
        if event is not None:
            normalized.append(event)
    return normalized


def _build_event_id(
    *,
    video_asset_id: str,
    candidate_clip_id: str,
    rally_segment_id: str | None,
    timestamp_s: float,
    setter_team_side: str,
    target_zone: str,
    set_type: str | None,
    set_success: bool,
    set_tempo: str,
) -> str:
    canonical_parts = [
        video_asset_id,
        candidate_clip_id,
        rally_segment_id or "",
        f"{timestamp_s:.3f}",
        setter_team_side,
        target_zone,
        set_type.strip() if set_type else "",
        "1" if set_success else "0",
        set_tempo,
    ]
    return f"set-{uuid5(NAMESPACE_URL, '|'.join(canonical_parts)).hex}"


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
