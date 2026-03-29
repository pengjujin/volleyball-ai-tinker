from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from backend.app.schemas.analytics import MatchAnalyticsSummary, TeamAnalyticsSummary
from backend.app.schemas.common import RulesetVariant, TeamSide
from backend.app.schemas.set_event import SetEvent


def summarize_set_events(
    *,
    video_asset_id: str,
    ruleset_variant: RulesetVariant,
    set_events: list[SetEvent],
) -> MatchAnalyticsSummary:
    by_team = [_build_team_summary(team_side, set_events) for team_side in _team_sides(set_events)]
    overall = _build_team_summary(TeamSide.unknown, set_events)
    return MatchAnalyticsSummary(
        video_asset_id=video_asset_id,
        ruleset_variant=ruleset_variant,
        generated_at=datetime.now(tz=timezone.utc),
        overall=overall,
        by_team=by_team,
    )


def _team_sides(set_events: list[SetEvent]) -> list[TeamSide]:
    sides = {event.setter_team_side for event in set_events if event.setter_team_side != TeamSide.unknown}
    return sorted(sides, key=lambda side: side.value)


def _build_team_summary(team_side: TeamSide, set_events: list[SetEvent]) -> TeamAnalyticsSummary:
    relevant_events = (
        set_events
        if team_side == TeamSide.unknown
        else [event for event in set_events if event.setter_team_side == team_side]
    )
    total = len(relevant_events)
    successful = sum(1 for event in relevant_events if event.set_success)
    success_rate = (successful / total) if total else 0.0
    tempo_distribution = Counter(event.set_tempo for event in relevant_events)
    zone_distribution = Counter(event.target_zone for event in relevant_events)
    return TeamAnalyticsSummary(
        team_side=team_side,
        total_set_attempts=total,
        successful_sets=successful,
        success_rate=success_rate,
        tempo_distribution=dict(tempo_distribution),
        target_zone_distribution=dict(zone_distribution),
    )
