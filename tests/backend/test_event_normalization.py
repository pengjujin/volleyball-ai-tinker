from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.app.schemas.common import SetTempo, TeamSide
from backend.app.schemas.gemini_analysis import CourtPoint, GeminiSetAnalysis
from backend.app.services.event_normalization import (
    normalize_gemini_set_analysis,
    normalize_gemini_set_analyses,
)


class EventNormalizationTest(unittest.TestCase):
    def test_normalizes_valid_analysis_with_provenance_and_coordinates(self) -> None:
        analysis = GeminiSetAnalysis(
            candidate_clip_id="video-1-cand-001",
            contains_set=True,
            setter_team_side=TeamSide.near_side,
            contact_time_s=12.3456,
            target_zone="  zone_4  ",
            set_type=" high outside ",
            set_success=True,
            success_reason=" hitter received an attackable ball ",
            set_tempo=SetTempo.medium,
            setter_court_position=CourtPoint(x=4.25, y=2.75),
            confidence=0.81234,
            notes=" clear second contact ",
        )
        created_at = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)

        event = normalize_gemini_set_analysis(
            analysis,
            video_asset_id="video-1",
            rally_segment_id="rally-9",
            created_at=created_at,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertTrue(event.set_event_id.startswith("set-"))
        self.assertEqual(event.video_asset_id, "video-1")
        self.assertEqual(event.rally_segment_id, "rally-9")
        self.assertEqual(event.source_candidate_clip_id, "video-1-cand-001")
        self.assertEqual(event.timestamp_s, 12.346)
        self.assertEqual(event.setter_team_side, TeamSide.near_side)
        self.assertEqual(event.target_zone, "zone_4")
        self.assertEqual(event.set_type, "high outside")
        self.assertTrue(event.set_success)
        self.assertEqual(event.success_reason, "hitter received an attackable ball")
        self.assertEqual(event.set_tempo, SetTempo.medium)
        self.assertEqual(event.setter_court_x, 4.25)
        self.assertEqual(event.setter_court_y, 2.75)
        self.assertEqual(event.confidence, 0.8123)
        self.assertEqual(event.notes, "clear second contact")
        self.assertEqual(event.created_at, created_at)

        repeated = normalize_gemini_set_analysis(
            analysis,
            video_asset_id="video-1",
            rally_segment_id="rally-9",
            created_at=created_at,
        )
        self.assertIsNotNone(repeated)
        assert repeated is not None
        self.assertEqual(event.set_event_id, repeated.set_event_id)

    def test_normalizes_without_optional_court_coordinates(self) -> None:
        analysis = GeminiSetAnalysis(
            candidate_clip_id="video-1-cand-002",
            contains_set=True,
            setter_team_side=TeamSide.far_side,
            contact_time_s=18.0,
            target_zone="zone_2",
            set_success=True,
            set_tempo=SetTempo.quick,
            confidence=0.95,
        )

        event = normalize_gemini_set_analysis(analysis, video_asset_id="video-1")

        self.assertIsNotNone(event)
        assert event is not None
        self.assertIsNone(event.setter_court_x)
        self.assertIsNone(event.setter_court_y)

    def test_filters_ignored_or_invalid_analyses(self) -> None:
        analyses = [
            GeminiSetAnalysis(
                candidate_clip_id="video-1-cand-003",
                contains_set=False,
                setter_team_side=TeamSide.near_side,
                contact_time_s=9.0,
                target_zone="zone_3",
                set_success=True,
                set_tempo=SetTempo.medium,
                confidence=0.6,
            ),
            GeminiSetAnalysis(
                candidate_clip_id="video-1-cand-004",
                contains_set=True,
                setter_team_side=TeamSide.near_side,
                contact_time_s=None,
                target_zone="zone_4",
                set_success=True,
                set_tempo=SetTempo.medium,
                confidence=0.6,
            ),
            GeminiSetAnalysis(
                candidate_clip_id="video-1-cand-005",
                contains_set=True,
                setter_team_side=TeamSide.near_side,
                contact_time_s=22.0,
                target_zone="  ",
                set_success=True,
                set_tempo=SetTempo.high_slow,
                confidence=0.6,
            ),
            GeminiSetAnalysis(
                candidate_clip_id="video-1-cand-006",
                contains_set=True,
                setter_team_side=TeamSide.unknown,
                contact_time_s=24.0,
                target_zone="zone_1",
                set_success=False,
                set_tempo=SetTempo.medium,
                confidence=0.77,
            ),
        ]

        events = normalize_gemini_set_analyses(analyses, video_asset_id="video-1")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source_candidate_clip_id, "video-1-cand-006")
        self.assertEqual(events[0].setter_team_side, TeamSide.unknown)
        self.assertFalse(events[0].set_success)


if __name__ == "__main__":
    unittest.main()
