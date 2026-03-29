from __future__ import annotations

import unittest

from backend.app.schemas import (
    MatchAnalyticsSummary,
    ProcessingJob,
    ProcessingStage,
    RallySegment,
    RulesetVariant,
    SetEvent,
    SetTempo,
    TeamAnalyticsSummary,
    TeamSide,
    VideoAsset,
    VideoAssetStatus,
    VideoSourceType,
)


class SchemaTest(unittest.TestCase):
    def test_video_asset_schema(self) -> None:
        asset = VideoAsset(
            video_asset_id="video-1",
            source_type=VideoSourceType.upload,
            source_url="file:///match.mp4",
            ruleset_variant=RulesetVariant.six_player,
        )
        self.assertEqual(asset.status, VideoAssetStatus.uploaded)
        self.assertEqual(asset.ruleset_variant, RulesetVariant.six_player)

    def test_processing_job_schema(self) -> None:
        job = ProcessingJob(
            job_id="job-1",
            video_asset_id="video-1",
            stage=ProcessingStage.queued,
        )
        self.assertEqual(job.progress, 0.0)

    def test_rally_segment_schema(self) -> None:
        segment = RallySegment(
            rally_segment_id="rally-1",
            video_asset_id="video-1",
            start_time_s=1.0,
            end_time_s=10.0,
            confidence=0.9,
        )
        self.assertEqual(segment.confidence, 0.9)

    def test_set_event_schema(self) -> None:
        event = SetEvent(
            set_event_id="set-1",
            video_asset_id="video-1",
            timestamp_s=12.5,
            setter_team_side=TeamSide.near_side,
            target_zone="zone_4",
            set_success=True,
            set_tempo=SetTempo.medium,
            confidence=0.8,
        )
        self.assertTrue(event.set_success)
        self.assertEqual(event.set_tempo, SetTempo.medium)

    def test_analytics_summary_schema(self) -> None:
        overall = TeamAnalyticsSummary(
            team_side=TeamSide.unknown,
            total_set_attempts=10,
            successful_sets=6,
            success_rate=0.6,
            tempo_distribution={SetTempo.quick: 2, SetTempo.medium: 4},
            target_zone_distribution={"zone_4": 5},
        )
        summary = MatchAnalyticsSummary(
            video_asset_id="video-1",
            ruleset_variant="6-player",
            overall=overall,
            by_team=[overall.model_copy(update={"team_side": TeamSide.near_side})],
        )
        self.assertEqual(summary.by_team[0].team_side, TeamSide.near_side)


if __name__ == "__main__":
    unittest.main()

