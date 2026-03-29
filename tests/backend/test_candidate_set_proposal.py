from __future__ import annotations

import unittest

from backend.app.schemas.preprocessing import FrameSignal
from backend.app.schemas.rally_segment import RallySegmentWindow
from backend.app.services.audio_features import detect_audio_bursts
from backend.app.services.candidate_set_proposal import (
    estimate_video_reduction,
    propose_candidate_set_clips,
)


def signal(
    timestamp_s: float,
    *,
    motion_score: float,
    ball_motion_score: float,
    audio_energy_score: float,
    on_court_score: float = 1.0,
    scene_cut: bool = False,
    replay_like: bool = False,
    crowd_like: bool = False,
) -> FrameSignal:
    return FrameSignal(
        timestamp_s=timestamp_s,
        motion_score=motion_score,
        ball_motion_score=ball_motion_score,
        audio_energy_score=audio_energy_score,
        on_court_score=on_court_score,
        scene_cut=scene_cut,
        replay_like=replay_like,
        crowd_like=crowd_like,
    )


class AudioFeatureTest(unittest.TestCase):
    def test_detect_audio_bursts_groups_spike_runs(self) -> None:
        bursts = detect_audio_bursts(
            [
                signal(0.0, motion_score=0.1, ball_motion_score=0.1, audio_energy_score=0.1),
                signal(0.5, motion_score=0.1, ball_motion_score=0.1, audio_energy_score=0.7),
                signal(1.0, motion_score=0.1, ball_motion_score=0.1, audio_energy_score=0.76),
                signal(2.2, motion_score=0.1, ball_motion_score=0.1, audio_energy_score=0.2),
                signal(3.0, motion_score=0.1, ball_motion_score=0.1, audio_energy_score=0.75),
            ]
        )

        self.assertEqual(len(bursts), 2)
        self.assertEqual(bursts[0].start_time_s, 0.5)
        self.assertEqual(bursts[0].peak_time_s, 1.0)
        self.assertGreaterEqual(bursts[0].peak_score, 0.76)
        self.assertEqual(bursts[1].start_time_s, 3.0)


class CandidateSetProposalTest(unittest.TestCase):
    def test_proposes_second_contact_clips_and_summary(self) -> None:
        frame_signals = [
            signal(0.0, motion_score=0.05, ball_motion_score=0.05, audio_energy_score=0.05),
            signal(0.5, motion_score=0.06, ball_motion_score=0.05, audio_energy_score=0.05),
            signal(1.0, motion_score=0.08, ball_motion_score=0.08, audio_energy_score=0.05),
            signal(1.5, motion_score=0.07, ball_motion_score=0.06, audio_energy_score=0.05),
            signal(2.0, motion_score=0.15, ball_motion_score=0.12, audio_energy_score=0.1),
            signal(2.5, motion_score=0.45, ball_motion_score=0.35, audio_energy_score=0.55),
            signal(3.0, motion_score=0.7, ball_motion_score=0.88, audio_energy_score=0.65),
            signal(3.5, motion_score=0.8, ball_motion_score=0.95, audio_energy_score=0.8),
            signal(4.0, motion_score=0.55, ball_motion_score=0.7, audio_energy_score=0.5),
            signal(4.5, motion_score=0.2, ball_motion_score=0.18, audio_energy_score=0.08),
            signal(5.0, motion_score=0.1, ball_motion_score=0.08, audio_energy_score=0.05),
            signal(6.0, motion_score=0.65, ball_motion_score=0.42, audio_energy_score=0.75),
            signal(6.5, motion_score=0.72, ball_motion_score=0.7, audio_energy_score=0.8),
            signal(7.0, motion_score=0.52, ball_motion_score=0.66, audio_energy_score=0.68),
            signal(7.5, motion_score=0.12, ball_motion_score=0.1, audio_energy_score=0.05),
            signal(8.0, motion_score=0.06, ball_motion_score=0.05, audio_energy_score=0.05),
            signal(10.0, motion_score=0.04, ball_motion_score=0.03, audio_energy_score=0.04, scene_cut=True),
            signal(12.0, motion_score=0.05, ball_motion_score=0.05, audio_energy_score=0.05),
            signal(12.5, motion_score=0.12, ball_motion_score=0.1, audio_energy_score=0.08),
            signal(13.0, motion_score=0.45, ball_motion_score=0.4, audio_energy_score=0.5),
            signal(13.5, motion_score=0.75, ball_motion_score=0.84, audio_energy_score=0.7),
            signal(14.0, motion_score=0.83, ball_motion_score=0.92, audio_energy_score=0.82),
            signal(14.5, motion_score=0.64, ball_motion_score=0.67, audio_energy_score=0.55),
            signal(15.0, motion_score=0.2, ball_motion_score=0.15, audio_energy_score=0.08),
            signal(15.5, motion_score=0.1, ball_motion_score=0.06, audio_energy_score=0.05),
            signal(16.0, motion_score=0.07, ball_motion_score=0.05, audio_energy_score=0.05, crowd_like=True),
            signal(17.0, motion_score=0.05, ball_motion_score=0.05, audio_energy_score=0.04),
            signal(18.0, motion_score=0.04, ball_motion_score=0.03, audio_energy_score=0.05),
        ]
        rally_windows = [
            RallySegmentWindow(start_time_s=2.0, end_time_s=8.0, confidence=0.9),
            RallySegmentWindow(start_time_s=12.0, end_time_s=15.5, confidence=0.85),
        ]

        result = propose_candidate_set_clips(
            video_asset_id="video-123",
            frame_signals=frame_signals,
            rally_windows=rally_windows,
            video_seconds_total=18.0,
        )

        self.assertEqual(result.summary.video_asset_id, "video-123")
        self.assertEqual(result.summary.rally_segments_detected, 2)
        self.assertEqual(result.summary.candidate_clips_detected, 3)
        self.assertEqual(result.summary.total_frames_sampled, len(frame_signals))
        self.assertGreater(result.summary.dead_time_frames_filtered, 0)
        self.assertAlmostEqual(result.summary.candidate_seconds_total, 8.1, delta=0.2)
        self.assertAlmostEqual(estimate_video_reduction(result.summary), 0.55, delta=0.1)

        self.assertEqual(len(result.candidate_clips), 3)
        first, second, third = result.candidate_clips

        self.assertEqual(first.start_time_s, 2.0)
        self.assertAlmostEqual(first.end_time_s, 4.65, delta=0.05)
        self.assertIn(first.trigger_label, {"ball_motion_peak", "audio_contact_burst"})
        self.assertGreaterEqual(first.confidence, 0.6)

        self.assertAlmostEqual(second.start_time_s, 5.35, delta=0.05)
        self.assertEqual(second.end_time_s, 8.0)
        self.assertIn(second.trigger_label, {"ball_motion_peak", "audio_contact_burst"})
        self.assertGreaterEqual(second.confidence, 0.6)

        self.assertAlmostEqual(third.start_time_s, 12.35, delta=0.05)
        self.assertAlmostEqual(third.end_time_s, 15.15, delta=0.05)
        self.assertIn(third.trigger_label, {"ball_motion_peak", "audio_contact_burst"})
        self.assertGreaterEqual(third.confidence, 0.6)

    def test_ignores_dead_time_and_low_confidence_frames(self) -> None:
        frame_signals = [
            signal(0.0, motion_score=0.05, ball_motion_score=0.05, audio_energy_score=0.04),
            signal(0.5, motion_score=0.04, ball_motion_score=0.04, audio_energy_score=0.03),
            signal(1.0, motion_score=0.06, ball_motion_score=0.05, audio_energy_score=0.04, replay_like=True),
            signal(1.5, motion_score=0.07, ball_motion_score=0.06, audio_energy_score=0.05),
        ]

        result = propose_candidate_set_clips(
            video_asset_id="video-empty",
            frame_signals=frame_signals,
            rally_windows=[RallySegmentWindow(start_time_s=0.0, end_time_s=1.5, confidence=0.4)],
        )

        self.assertEqual(result.candidate_clips, [])
        self.assertEqual(result.summary.candidate_clips_detected, 0)
        self.assertGreater(result.summary.dead_time_frames_filtered, 0)
        self.assertEqual(result.summary.candidate_seconds_total, 0.0)


if __name__ == "__main__":
    unittest.main()
