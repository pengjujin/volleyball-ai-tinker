from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from backend.app.schemas.preprocessing import FrameSignal, PreprocessingSummary
from backend.app.schemas.rally_segment import RallySegmentWindow
from backend.app.services.frame_sampling import (
    filter_dead_time_frames,
    is_active_frame,
    score_frame_activity,
    summarize_activity,
)

_DEFAULT_GAP_TOLERANCE_S = 0.85
_DEFAULT_MIN_DURATION_S = 1.25
_SHORT_WINDOW_PENALTY = 0.12


@dataclass(frozen=True)
class RallyWindowMetrics:
    start_time_s: float
    end_time_s: float
    frame_count: int
    avg_activity: float
    peak_activity: float

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_time_s - self.start_time_s)


def detect_rally_windows(
    frame_signals: Sequence[FrameSignal],
    *,
    activity_threshold: float = 0.45,
    gap_tolerance_s: float = _DEFAULT_GAP_TOLERANCE_S,
    min_duration_s: float = _DEFAULT_MIN_DURATION_S,
) -> list[RallySegmentWindow]:
    active_frames = filter_dead_time_frames(
        frame_signals,
        activity_threshold=activity_threshold,
    )
    if not active_frames:
        return []

    groups: list[list[FrameSignal]] = []
    current_group: list[FrameSignal] = [active_frames[0]]

    for signal in active_frames[1:]:
        previous = current_group[-1]
        gap_s = signal.timestamp_s - previous.timestamp_s
        if gap_s <= gap_tolerance_s:
            current_group.append(signal)
            continue

        groups.append(current_group)
        current_group = [signal]

    groups.append(current_group)

    windows: list[RallySegmentWindow] = []
    for group in groups:
        metrics = _build_window_metrics(group)
        if metrics.duration_s < min_duration_s and metrics.frame_count < 2:
            continue

        confidence = _build_window_confidence(metrics, min_duration_s=min_duration_s)
        windows.append(
            RallySegmentWindow(
                start_time_s=metrics.start_time_s,
                end_time_s=metrics.end_time_s,
                confidence=confidence,
            )
        )

    return windows


def build_preprocessing_summary(
    *,
    video_asset_id: str,
    frame_signals: Sequence[FrameSignal],
    sampled_fps: float,
    rally_windows: Sequence[RallySegmentWindow],
) -> PreprocessingSummary:
    active_frames = filter_dead_time_frames(frame_signals)
    video_seconds_total = _estimate_video_span(frame_signals)
    candidate_seconds_total = sum(
        max(0.0, window.end_time_s - window.start_time_s) for window in rally_windows
    )
    return PreprocessingSummary(
        video_asset_id=video_asset_id,
        sampled_fps=sampled_fps,
        total_frames_sampled=len(frame_signals),
        dead_time_frames_filtered=max(0, len(frame_signals) - len(active_frames)),
        rally_segments_detected=len(rally_windows),
        candidate_clips_detected=len(rally_windows),
        candidate_seconds_total=candidate_seconds_total,
        video_seconds_total=video_seconds_total,
    )


def _build_window_metrics(group: Sequence[FrameSignal]) -> RallyWindowMetrics:
    start_time_s = group[0].timestamp_s
    end_time_s = group[-1].timestamp_s
    activities = [score_frame_activity(signal) for signal in group]
    return RallyWindowMetrics(
        start_time_s=start_time_s,
        end_time_s=end_time_s,
        frame_count=len(group),
        avg_activity=mean(activities),
        peak_activity=max(activities),
    )


def _build_window_confidence(
    metrics: RallyWindowMetrics,
    *,
    min_duration_s: float,
) -> float:
    duration_component = min(metrics.duration_s / max(min_duration_s, 1e-6), 1.0)
    density_component = min(metrics.frame_count / 6.0, 1.0)
    confidence = (
        (0.70 * metrics.avg_activity)
        + (0.15 * metrics.peak_activity)
        + (0.10 * duration_component)
        + (0.05 * density_component)
    )

    if metrics.frame_count >= 3 and metrics.avg_activity >= 0.6:
        confidence += 0.08

    if metrics.peak_activity >= 0.75:
        confidence += 0.10

    if metrics.duration_s >= 1.0:
        confidence += 0.04

    if metrics.duration_s < min_duration_s:
        confidence -= _SHORT_WINDOW_PENALTY

    return max(0.0, min(1.0, confidence))


def _estimate_video_span(frame_signals: Sequence[FrameSignal]) -> float:
    if len(frame_signals) < 2:
        return 0.0
    return max(0.0, frame_signals[-1].timestamp_s - frame_signals[0].timestamp_s)


def detect_active_rally_frames(
    frame_signals: Sequence[FrameSignal],
    *,
    activity_threshold: float = 0.45,
) -> list[FrameSignal]:
    return [
        signal
        for signal in frame_signals
        if is_active_frame(signal, activity_threshold=activity_threshold)
    ]
