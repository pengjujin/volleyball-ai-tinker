from __future__ import annotations

from types import SimpleNamespace
import unittest

from backend.app.integrations.gemini_client import (
    GeminiClient,
    GeminiClientConfig,
    GeminiClientError,
    GeminiResponseValidationError,
    _extract_file_state_name,
)
from backend.app.schemas.common import SetTempo, TeamSide
from backend.app.schemas.preprocessing import CandidateClip
from backend.app.services.gemini_set_analysis import (
    GeminiSetAnalysisService,
    analyze_candidate_clips,
)


def candidate_clip(
    candidate_clip_id: str = "cand-1",
    *,
    confidence: float = 0.81,
    trigger_label: str = "ball_motion_peak",
    start_time_s: float = 12.0,
    end_time_s: float = 14.0,
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


class GeminiClientTest(unittest.TestCase):
    def test_stub_response_is_deterministic_and_valid(self) -> None:
        client = GeminiClient()
        clip = candidate_clip(confidence=0.78, start_time_s=12.0, end_time_s=14.0)

        analysis = client.analyze_candidate_clip(clip)

        self.assertEqual(analysis.candidate_clip_id, clip.candidate_clip_id)
        self.assertTrue(analysis.contains_set)
        self.assertEqual(analysis.setter_team_side, TeamSide.near_side)
        self.assertEqual(analysis.set_tempo, SetTempo.quick)
        self.assertIsNotNone(analysis.setter_court_position)
        self.assertGreaterEqual(analysis.confidence, 0.78)

    def test_supplied_payload_is_strictly_validated(self) -> None:
        client = GeminiClient()
        clip = candidate_clip(candidate_clip_id="cand-2", confidence=0.74)

        analysis = client.analyze_candidate_clip(
            clip,
            raw_response={
                "candidate_clip_id": "cand-2",
                "contains_set": True,
                "setter_team_side": "far_side",
                "contact_time_s": 13.25,
                "target_zone": "zone_4",
                "set_type": "outside",
                "set_success": True,
                "success_reason": "attackable_ball",
                "set_tempo": "medium",
                "setter_court_position": {"x": 4.2, "y": 2.6},
                "confidence": 0.93,
                "notes": "manual payload",
            },
        )

        self.assertEqual(analysis.setter_team_side, TeamSide.far_side)
        self.assertEqual(analysis.set_tempo, SetTempo.medium)
        self.assertAlmostEqual(analysis.contact_time_s or 0.0, 13.25)
        self.assertEqual(analysis.target_zone, "zone_4")
        self.assertEqual(analysis.set_success, True)
        self.assertEqual(analysis.success_reason, "attackable_ball")
        self.assertEqual(analysis.confidence, 0.93)

    def test_rejects_malformed_payloads(self) -> None:
        client = GeminiClient()
        clip = candidate_clip(candidate_clip_id="cand-3")

        with self.assertRaises(GeminiResponseValidationError):
            client.analyze_candidate_clip(
                clip,
                raw_response={
                    "candidate_clip_id": "cand-3",
                    "contains_set": True,
                    "setter_team_side": "near_side",
                    "contact_time_s": 13.1,
                    "target_zone": "zone_2",
                    "set_success": True,
                    "set_tempo": "quick",
                    "confidence": 0.8,
                    "unexpected_field": True,
                },
            )

        with self.assertRaises(GeminiResponseValidationError):
            client.analyze_candidate_clip(
                clip,
                raw_response={
                    "candidate_clip_id": "cand-3",
                    "contains_set": True,
                    "setter_team_side": "near_side",
                    "contact_time_s": 13.1,
                    "target_zone": "zone_2",
                    "set_success": True,
                    "confidence": 0.8,
                },
            )

    def test_wait_for_file_active_polls_until_active(self) -> None:
        client = GeminiClient(
            config=GeminiClientConfig(
                file_poll_interval_s=0.0,
                file_ready_timeout_s=1.0,
            )
        )
        states = iter(
            [
                SimpleNamespace(name="PROCESSING"),
                SimpleNamespace(name="ACTIVE"),
            ]
        )

        class FakeFiles:
            def get(self, *, name: str):
                return SimpleNamespace(
                    name=name,
                    uri="https://files.example/video",
                    mime_type="video/mp4",
                    state=next(states),
                )

        class FakeLiveClient:
            def __init__(self) -> None:
                self.files = FakeFiles()

        client._live_client = FakeLiveClient()
        uploaded = SimpleNamespace(
            name="files/123",
            uri="https://files.example/video",
            mime_type="video/mp4",
            state=SimpleNamespace(name="PROCESSING"),
        )

        active_file = client._wait_for_file_active(uploaded, "cand-live")

        self.assertEqual(_extract_file_state_name(active_file), "ACTIVE")

    def test_wait_for_file_active_raises_on_terminal_failure_state(self) -> None:
        client = GeminiClient(
            config=GeminiClientConfig(
                file_poll_interval_s=0.0,
                file_ready_timeout_s=1.0,
            )
        )

        class FakeFiles:
            def get(self, *, name: str):
                return SimpleNamespace(
                    name=name,
                    uri="https://files.example/video",
                    mime_type="video/mp4",
                    state=SimpleNamespace(name="FAILED"),
                )

        class FakeLiveClient:
            def __init__(self) -> None:
                self.files = FakeFiles()

        client._live_client = FakeLiveClient()
        uploaded = SimpleNamespace(
            name="files/123",
            uri="https://files.example/video",
            mime_type="video/mp4",
            state=SimpleNamespace(name="PROCESSING"),
        )

        with self.assertRaises(GeminiClientError):
            client._wait_for_file_active(uploaded, "cand-live")

    def test_extract_file_state_name_handles_enum_like_and_string_values(self) -> None:
        self.assertEqual(
            _extract_file_state_name(SimpleNamespace(state=SimpleNamespace(name="ACTIVE"))),
            "ACTIVE",
        )
        self.assertEqual(
            _extract_file_state_name(SimpleNamespace(state="PROCESSING")),
            "PROCESSING",
        )
        self.assertIsNone(_extract_file_state_name(SimpleNamespace(state=None)))


class GeminiSetAnalysisServiceTest(unittest.TestCase):
    def test_low_confidence_candidates_are_downgraded(self) -> None:
        service = GeminiSetAnalysisService(minimum_candidate_confidence=0.5)
        clip = candidate_clip(candidate_clip_id="cand-4", confidence=0.22)

        analysis = service.analyze_candidate_clip(
            clip,
            raw_response={
                "candidate_clip_id": "cand-4",
                "contains_set": True,
                "setter_team_side": "near_side",
                "contact_time_s": 13.0,
                "target_zone": "zone_3",
                "set_type": "tempo",
                "set_success": True,
                "success_reason": "attackable_ball",
                "set_tempo": "quick",
                "confidence": 0.91,
            },
        )

        self.assertEqual(analysis.confidence, 0.22)
        self.assertIn("below threshold", analysis.notes or "")
        self.assertEqual(analysis.target_zone, "zone_3")

    def test_batch_analysis_uses_raw_responses_map(self) -> None:
        clips = [
            candidate_clip(candidate_clip_id="cand-a", confidence=0.72, start_time_s=10.0),
            candidate_clip(candidate_clip_id="cand-b", confidence=0.64, start_time_s=11.0),
        ]

        result = analyze_candidate_clips(
            clips,
            raw_responses={
                "cand-a": {
                    "candidate_clip_id": "cand-a",
                    "contains_set": True,
                    "setter_team_side": "near_side",
                    "contact_time_s": 10.8,
                    "target_zone": "zone_4",
                    "set_type": "outside",
                    "set_success": True,
                    "success_reason": "attackable_ball",
                    "set_tempo": "quick",
                    "confidence": 0.84,
                },
                "cand-b": {
                    "candidate_clip_id": "cand-b",
                    "contains_set": False,
                    "setter_team_side": "unknown",
                    "confidence": 0.41,
                },
            },
        )

        self.assertEqual(len(result.analyses), 2)
        self.assertEqual(result.analyses[0].candidate_clip_id, "cand-a")
        self.assertTrue(result.analyses[0].contains_set)
        self.assertFalse(result.analyses[1].contains_set)
        self.assertEqual(result.low_confidence_candidate_clips, [])


if __name__ == "__main__":
    unittest.main()
