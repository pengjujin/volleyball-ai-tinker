from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.common import SetTempo, TeamSide


class SetEvent(BaseModel):
    set_event_id: str
    video_asset_id: str
    rally_segment_id: str | None = None
    source_candidate_clip_id: str | None = None
    timestamp_s: float
    setter_team_side: TeamSide
    target_zone: str
    set_type: str | None = None
    set_success: bool
    success_reason: str | None = None
    set_tempo: SetTempo
    setter_court_x: float | None = None
    setter_court_y: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
    created_at: datetime | None = None


class SetEventCreate(BaseModel):
    timestamp_s: float
    setter_team_side: TeamSide
    target_zone: str
    set_type: str | None = None
    set_success: bool
    success_reason: str | None = None
    set_tempo: SetTempo
    source_candidate_clip_id: str | None = None
    setter_court_x: float | None = None
    setter_court_y: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
