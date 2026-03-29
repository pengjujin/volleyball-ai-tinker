from __future__ import annotations

import inspect
import unittest

from backend.app.schemas.preprocessing import FrameSignal
from backend.app.services.frame_sampling import filter_dead_time_frames, score_frame_activity
from backend.app.services.rally_segmentation import (
    build_preprocessing_summary,
    detect_active_rally_frames,
    detect_rally_windows,
)


class RallySegmentationTest(unittest.TestCase):
    def test_dead_time_filter_removes_obvious_pause_frames(self) -> None:
        frames = [
            FrameSignal(
                timestamp_s=0.0,
                motion_score=0.04,
                ball_motion_score=0.0,
                on_court_score=0.15,
                audio_energy_score=0.02,
                scene_cut=True,
            ),
            FrameSignal(
                timestamp_s=0.5,
                motion_score=0.08,
                ball_motion_score=0.0,
                on_court_score=0.18,
                audio_energy_score=0.03,
                crowd_like=True,
            ),
            FrameSignal(
                timestamp_s=1.0,
                motion_score=0.78,
                ball_motion_score=0.64,
                on_court_score=0.95,
                audio_energy_score=0.61,
            ),
            FrameSignal(
                timestamp_s=1.5,
                motion_score=0.82,
                ball_motion_score=0.70,
                on_court_score=0.96,
                audio_energy_score=0.68,
            ),
        ]

        active_frames = filter_dead_time_frames(frames)

        self.assertEqual([signal.timestamp_s for signal in active_frames], [1.0, 1.5])
        self.assertGreater(score_frame_activity(active_frames[0]), 0.7)

    def test_detect_rally_windows_groups_contiguous_active_frames(self) -> None:
        frames = [
            FrameSignal(
                timestamp_s=0.0,
                motion_score=0.04,
                ball_motion_score=0.0,
                on_court_score=0.2,
                audio_energy_score=0.03,
                scene_cut=True,
            ),
            FrameSignal(
                timestamp_s=2.0,
                motion_score=0.70,
                ball_motion_score=0.58,
                on_court_score=0.93,
                audio_energy_score=0.52,
            ),
            FrameSignal(
                timestamp_s=2.6,
                motion_score=0.76,
                ball_motion_score=0.73,
                on_court_score=0.97,
                audio_energy_score=0.58,
            ),
            FrameSignal(
                timestamp_s=3.1,
                motion_score=0.72,
                ball_motion_score=0.67,
                on_court_score=0.95,
                audio_energy_score=0.60,
            ),
            FrameSignal(
                timestamp_s=7.0,
                motion_score=0.10,
                ball_motion_score=0.0,
                on_court_score=0.15,
                audio_energy_score=0.02,
                replay_like=True,
            ),
            FrameSignal(
                timestamp_s=8.2,
                motion_score=0.83,
                ball_motion_score=0.77,
                on_court_score=0.96,
                audio_energy_score=0.69,
            ),
            FrameSignal(
                timestamp_s=8.7,
                motion_score=0.79,
                ball_motion_score=0.72,
                on_court_score=0.95,
                audio_energy_score=0.71,
            ),
        ]

        windows = detect_rally_windows(frames)

        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0].start_time_s, 2.0)
        self.assertEqual(windows[0].end_time_s, 3.1)
        self.assertEqual(windows[1].start_time_s, 8.2)
        self.assertEqual(windows[1].end_time_s, 8.7)
        self.assertGreater(windows[0].confidence, 0.7)
        self.assertGreater(windows[1].confidence, 0.7)
        self.assertNotAlmostEqual(windows[0].confidence, windows[1].confidence)

    def test_summary_counts_dead_time_and_video_span(self) -> None:
        frames = [
            FrameSignal(
                timestamp_s=0.0,
                motion_score=0.05,
                ball_motion_score=0.0,
                on_court_score=0.1,
                audio_energy_score=0.01,
                crowd_like=True,
            ),
            FrameSignal(
                timestamp_s=1.0,
                motion_score=0.74,
                ball_motion_score=0.61,
                on_court_score=0.94,
                audio_energy_score=0.63,
            ),
            FrameSignal(
                timestamp_s=1.5,
                motion_score=0.77,
                ball_motion_score=0.69,
                on_court_score=0.95,
                audio_energy_score=0.67,
            ),
        ]
        windows = detect_rally_windows(frames)

        summary = build_preprocessing_summary(
            video_asset_id="video-1",
            frame_signals=frames,
            sampled_fps=2.0,
            rally_windows=windows,
        )

        self.assertEqual(summary.video_asset_id, "video-1")
        self.assertEqual(summary.total_frames_sampled, 3)
        self.assertEqual(summary.dead_time_frames_filtered, 1)
        self.assertEqual(summary.rally_segments_detected, 1)
        self.assertEqual(summary.candidate_clips_detected, 1)
        self.assertAlmostEqual(summary.video_seconds_total, 1.5)
        self.assertAlmostEqual(summary.candidate_seconds_total, 0.5)

    def test_segmentation_is_formation_agnostic(self) -> None:
        signature = inspect.signature(detect_rally_windows)
        self.assertNotIn("player_count", signature.parameters)
        self.assertNotIn("formation", signature.parameters)

        frames = [
            FrameSignal(
                timestamp_s=0.0,
                motion_score=0.74,
                ball_motion_score=0.60,
                on_court_score=0.96,
                audio_energy_score=0.55,
            ),
            FrameSignal(
                timestamp_s=0.4,
                motion_score=0.79,
                ball_motion_score=0.66,
                on_court_score=0.97,
                audio_energy_score=0.62,
            ),
            FrameSignal(
                timestamp_s=0.8,
                motion_score=0.76,
                ball_motion_score=0.71,
                on_court_score=0.95,
                audio_energy_score=0.64,
            ),
        ]

        active_frames = detect_active_rally_frames(frames)
        windows = detect_rally_windows(frames)

        self.assertEqual(len(active_frames), 3)
        self.assertEqual(len(windows), 1)
        self.assertGreater(windows[0].confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
