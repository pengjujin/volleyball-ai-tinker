from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.common import RulesetVariant, SetTempo, TeamSide


class TeamAnalyticsSummary(BaseModel):
    team_side: TeamSide
    total_set_attempts: int = 0
    successful_sets: int = 0
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    tempo_distribution: dict[SetTempo, int] = Field(default_factory=dict)
    target_zone_distribution: dict[str, int] = Field(default_factory=dict)


class MatchAnalyticsSummary(BaseModel):
    video_asset_id: str
    ruleset_variant: RulesetVariant
    generated_at: datetime | None = None
    overall: TeamAnalyticsSummary
    by_team: list[TeamAnalyticsSummary] = Field(default_factory=list)
