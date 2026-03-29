from __future__ import annotations

import unittest

from backend.app.schemas.preprocessing import CandidateClip
from backend.app.services.analyze_candidate_clips import (
    analyze_candidate_clips_to_events,
)


def candidate_clip(
    candidate_clip_id: str,
    *,
    confidence: float,
    trigger_label: str,
    start_time_s: float,
    end_time_s: float,
) -> CandidateClip:
    return CandidateClip(
        candidate_clip_id=candidate_clip_id,
        video_asset_id="video-1",
        rally_segment_id="rally-1",
        start_time_s=start_time_s,
        end_time_s=end_time_s,
        trigger_label=trigger_label,
        confidence=confidence,
    )


class AnalyzeCandidateClipsTest(unittest.TestCase):
    def test_combines_analysis_and_event_normalization(self) -> None:
        result = analyze_candidate_clips_to_events(
            video_asset_id="video-1",
            candidate_clips=[
                candidate_clip(
                    "cand-1",
                    confidence=0.82,
                    trigger_label="ball_motion_peak",
                    start_time_s=12.0,
                    end_time_s=14.0,
                ),
                candidate_clip(
                    "cand-2",
                    confidence=0.28,
                    trigger_label="court_motion_cluster",
                    start_time_s=20.0,
                    end_time_s=22.0,
                ),
            ],
            raw_responses={
                "cand-1": {
                    "candidate_clip_id": "cand-1",
                    "contains_set": True,
                    "setter_team_side": "near_side",
                    "contact_time_s": 13.1,
                    "target_zone": "zone_4",
                    "set_type": "outside",
                    "set_success": True,
                    "success_reason": "attackable_ball",
                    "set_tempo": "quick",
                    "confidence": 0.91,
                },
                "cand-2": {
                    "candidate_clip_id": "cand-2",
                    "contains_set": False,
                    "setter_team_side": "unknown",
                    "confidence": 0.41,
                },
            },
        )

        self.assertEqual(len(result.analyses), 2)
        self.assertEqual(len(result.set_events), 1)
        self.assertEqual(result.set_events[0].source_candidate_clip_id, "cand-1")
        self.assertEqual(result.low_confidence_candidate_clips, ["cand-2"])


if __name__ == "__main__":
    unittest.main()
