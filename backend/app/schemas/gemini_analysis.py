from __future__ import annotations

from pydantic import BaseModel, Field

from backend.app.schemas.common import SetTempo, TeamSide


class CourtPoint(BaseModel):
    x: float
    y: float


class GeminiSetAnalysis(BaseModel):
    candidate_clip_id: str
    contains_set: bool
    setter_team_side: TeamSide = TeamSide.unknown
    contact_time_s: float | None = Field(default=None, ge=0.0)
    target_zone: str | None = None
    set_type: str | None = None
    set_success: bool | None = None
    success_reason: str | None = None
    set_tempo: SetTempo | None = None
    setter_court_position: CourtPoint | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
