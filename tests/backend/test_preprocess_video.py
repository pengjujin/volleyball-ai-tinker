from __future__ import annotations

import unittest

from backend.app.schemas.preprocessing import FrameSignal
from backend.app.services.preprocess_video import preprocess_video_signals


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


class PreprocessVideoTest(unittest.TestCase):
    def test_pipeline_returns_rally_windows_candidate_clips_and_reduction(self) -> None:
        frame_signals = [
            signal(0.0, motion_score=0.03, ball_motion_score=0.02, audio_energy_score=0.02, crowd_like=True),
            signal(1.0, motion_score=0.08, ball_motion_score=0.05, audio_energy_score=0.04),
            signal(2.0, motion_score=0.18, ball_motion_score=0.14, audio_energy_score=0.10),
            signal(2.5, motion_score=0.48, ball_motion_score=0.34, audio_energy_score=0.52),
            signal(3.0, motion_score=0.74, ball_motion_score=0.87, audio_energy_score=0.64),
            signal(3.5, motion_score=0.82, ball_motion_score=0.93, audio_energy_score=0.79),
            signal(4.0, motion_score=0.58, ball_motion_score=0.72, audio_energy_score=0.56),
            signal(4.5, motion_score=0.16, ball_motion_score=0.12, audio_energy_score=0.07),
            signal(7.0, motion_score=0.05, ball_motion_score=0.03, audio_energy_score=0.02, scene_cut=True),
            signal(9.0, motion_score=0.20, ball_motion_score=0.18, audio_energy_score=0.12),
            signal(9.5, motion_score=0.55, ball_motion_score=0.41, audio_energy_score=0.58),
            signal(10.0, motion_score=0.78, ball_motion_score=0.88, audio_energy_score=0.72),
            signal(10.5, motion_score=0.84, ball_motion_score=0.91, audio_energy_score=0.80),
            signal(11.0, motion_score=0.62, ball_motion_score=0.68, audio_energy_score=0.54),
            signal(11.5, motion_score=0.14, ball_motion_score=0.10, audio_energy_score=0.05),
        ]

        result = preprocess_video_signals(
            video_asset_id="video-pipeline",
            frame_signals=frame_signals,
            sampled_fps=2.0,
        )

        self.assertEqual(len(result.rally_windows), 2)
        self.assertGreaterEqual(len(result.candidate_clips), 2)
        self.assertEqual(result.summary.video_asset_id, "video-pipeline")
        self.assertEqual(result.summary.rally_segments_detected, 2)
        self.assertEqual(
            result.summary.candidate_clips_detected,
            len(result.candidate_clips),
        )
        self.assertGreater(result.reduction_estimate, 0.0)
        self.assertLess(result.reduction_estimate, 1.0)


if __name__ == "__main__":
    unittest.main()
