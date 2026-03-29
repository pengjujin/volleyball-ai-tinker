from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from uuid import uuid4

from backend.app.schemas.preprocessing import (
    CandidateClip,
    FrameSignal,
    PreprocessingSummary,
)
from backend.app.schemas.rally_segment import RallySegmentWindow
from backend.app.services.audio_features import (
    AudioBurst,
    burst_peak_score,
    detect_audio_bursts,
    in_audio_burst,
)


@dataclass(frozen=True, slots=True)
class CandidateSetProposalResult:
    candidate_clips: list[CandidateClip]
    summary: PreprocessingSummary


def propose_candidate_set_clips(
    *,
    video_asset_id: str,
    frame_signals: list[FrameSignal],
    rally_windows: list[RallySegmentWindow],
    video_seconds_total: float | None = None,
    sampled_fps: float | None = None,
    pre_roll_s: float = 1.15,
    post_roll_s: float = 1.65,
    min_clip_duration_s: float = 1.8,
    max_clip_duration_s: float = 4.0,
    min_event_score: float = 0.58,
    dedupe_gap_s: float = 0.85,
) -> CandidateSetProposalResult:
    ordered_signals = sorted(frame_signals, key=lambda signal: signal.timestamp_s)
    ordered_windows = sorted(
        rally_windows, key=lambda window: (window.start_time_s, window.end_time_s)
    )
    audio_bursts = detect_audio_bursts(ordered_signals)
    candidate_points: list[_CandidatePoint] = []

    for window in ordered_windows:
        window_signals = [
            signal
            for signal in ordered_signals
            if window.start_time_s <= signal.timestamp_s <= window.end_time_s
        ]

        if not window_signals:
            continue

        for index, signal in enumerate(window_signals):
            if _is_dead_time(signal):
                continue

            score = _event_score(signal, window, audio_bursts)
            if score < min_event_score:
                continue

            if not _is_local_peak(window_signals, index, score, audio_bursts):
                continue

            confidence = min(1.0, round(score, 4))
            trigger_label = _trigger_label(signal, audio_bursts)
            candidate_points.append(
                _CandidatePoint(
                    video_asset_id=video_asset_id,
                    rally_segment_id=None,
                    timestamp_s=signal.timestamp_s,
                    confidence=confidence,
                    trigger_label=trigger_label,
                    window_start_s=window.start_time_s,
                    window_end_s=window.end_time_s,
                )
            )

    merged_points = _dedupe_candidate_points(candidate_points, dedupe_gap_s=dedupe_gap_s)
    clips = [
        _build_candidate_clip(
            video_asset_id=video_asset_id,
            index=index,
            point=point,
            rally_windows=ordered_windows,
            pre_roll_s=pre_roll_s,
            post_roll_s=post_roll_s,
            min_clip_duration_s=min_clip_duration_s,
            max_clip_duration_s=max_clip_duration_s,
        )
        for index, point in enumerate(merged_points, start=1)
    ]

    total_seconds = _resolve_video_seconds_total(
        ordered_signals, rally_windows=ordered_windows, fallback=video_seconds_total
    )
    effective_fps = _resolve_sampled_fps(ordered_signals, fallback=sampled_fps)

    summary = PreprocessingSummary(
        video_asset_id=video_asset_id,
        sampled_fps=effective_fps,
        total_frames_sampled=len(ordered_signals),
        dead_time_frames_filtered=_count_dead_time_frames(ordered_signals, ordered_windows),
        rally_segments_detected=len(ordered_windows),
        candidate_clips_detected=len(clips),
        candidate_seconds_total=round(
            sum(clip.end_time_s - clip.start_time_s for clip in clips), 3
        ),
        video_seconds_total=round(total_seconds, 3),
    )

    return CandidateSetProposalResult(candidate_clips=clips, summary=summary)


def estimate_video_reduction(summary: PreprocessingSummary) -> float:
    if summary.video_seconds_total <= 0:
        return 0.0
    proposed_seconds = min(summary.candidate_seconds_total, summary.video_seconds_total)
    reduction = 1.0 - (proposed_seconds / summary.video_seconds_total)
    return max(0.0, min(1.0, round(reduction, 4)))


@dataclass(frozen=True, slots=True)
class _CandidatePoint:
    video_asset_id: str
    rally_segment_id: str | None
    timestamp_s: float
    confidence: float
    trigger_label: str
    window_start_s: float
    window_end_s: float


def _is_dead_time(signal: FrameSignal) -> bool:
    if signal.scene_cut or signal.replay_like or signal.crowd_like:
        return True

    if signal.on_court_score < 0.3:
        return True

    if signal.motion_score < 0.08 and signal.ball_motion_score < 0.08 and signal.audio_energy_score < 0.08:
        return True

    return False


def _event_score(
    signal: FrameSignal,
    window: RallySegmentWindow,
    audio_bursts: list[AudioBurst],
) -> float:
    audio_score = signal.audio_energy_score
    if in_audio_burst(signal.timestamp_s, audio_bursts):
        audio_score = max(audio_score, burst_peak_score(signal.timestamp_s, audio_bursts))

    score = (
        0.45 * signal.ball_motion_score
        + 0.25 * signal.motion_score
        + 0.2 * audio_score
        + 0.1 * signal.on_court_score
    )
    score += 0.1 * window.confidence

    if signal.ball_motion_score >= 0.75:
        score += 0.08

    if signal.audio_energy_score >= 0.7:
        score += 0.05

    return min(1.0, round(score, 4))


def _is_local_peak(
    window_signals: list[FrameSignal],
    index: int,
    score: float,
    audio_bursts: list[AudioBurst],
) -> bool:
    signal = window_signals[index]
    left = window_signals[index - 1] if index > 0 else None
    right = window_signals[index + 1] if index + 1 < len(window_signals) else None

    left_score = _peer_score(left, audio_bursts) if left is not None else -1.0
    right_score = _peer_score(right, audio_bursts) if right is not None else -1.0

    return score >= left_score and score >= right_score


def _peer_score(signal: FrameSignal, audio_bursts: list[AudioBurst]) -> float:
    return _event_score(
        signal,
        RallySegmentWindow(
            start_time_s=signal.timestamp_s,
            end_time_s=signal.timestamp_s,
            confidence=0.0,
        ),
        audio_bursts,
    )


def _trigger_label(signal: FrameSignal, audio_bursts: list[AudioBurst]) -> str:
    burst_score = burst_peak_score(signal.timestamp_s, audio_bursts)
    if signal.ball_motion_score >= 0.72 and signal.ball_motion_score >= signal.motion_score:
        return "ball_motion_peak"
    if burst_score >= 0.7 or signal.audio_energy_score >= 0.72:
        return "audio_contact_burst"
    return "court_motion_cluster"


def _dedupe_candidate_points(
    points: list[_CandidatePoint],
    *,
    dedupe_gap_s: float,
) -> list[_CandidatePoint]:
    if not points:
        return []

    ordered = sorted(points, key=lambda point: (point.timestamp_s, -point.confidence))
    merged: list[_CandidatePoint] = []
    current_cluster: list[_CandidatePoint] = [ordered[0]]

    for point in ordered[1:]:
        if point.timestamp_s - current_cluster[-1].timestamp_s <= dedupe_gap_s:
            current_cluster.append(point)
            continue

        merged.append(_select_cluster_anchor(current_cluster))
        current_cluster = [point]

    merged.append(_select_cluster_anchor(current_cluster))
    return merged


def _select_cluster_anchor(cluster: list[_CandidatePoint]) -> _CandidatePoint:
    return max(cluster, key=lambda point: (point.confidence, -point.timestamp_s))


def _build_candidate_clip(
    *,
    video_asset_id: str,
    index: int,
    point: _CandidatePoint,
    rally_windows: list[RallySegmentWindow],
    pre_roll_s: float,
    post_roll_s: float,
    min_clip_duration_s: float,
    max_clip_duration_s: float,
) -> CandidateClip:
    rally_window = _find_covering_window(point.timestamp_s, rally_windows)

    start_time_s = max(point.window_start_s, point.timestamp_s - pre_roll_s)
    end_time_s = min(point.window_end_s, point.timestamp_s + post_roll_s)

    if rally_window is not None:
        start_time_s = max(start_time_s, rally_window.start_time_s)
        end_time_s = min(end_time_s, rally_window.end_time_s)

    duration = end_time_s - start_time_s
    if duration < min_clip_duration_s:
        shortfall = min_clip_duration_s - duration
        start_time_s = max(point.window_start_s, start_time_s - shortfall / 2)
        end_time_s = min(point.window_end_s, end_time_s + shortfall / 2)

    duration = end_time_s - start_time_s
    if duration > max_clip_duration_s:
        end_time_s = start_time_s + max_clip_duration_s

    return CandidateClip(
        candidate_clip_id=f"{video_asset_id}-cand-{index:03d}-{uuid4().hex[:8]}",
        video_asset_id=video_asset_id,
        rally_segment_id=point.rally_segment_id,
        start_time_s=round(start_time_s, 3),
        end_time_s=round(end_time_s, 3),
        trigger_label=point.trigger_label,
        confidence=point.confidence,
    )


def _find_covering_window(
    timestamp_s: float, rally_windows: list[RallySegmentWindow]
) -> RallySegmentWindow | None:
    for window in rally_windows:
        if window.start_time_s <= timestamp_s <= window.end_time_s:
            return window
    return None


def _count_dead_time_frames(
    signals: list[FrameSignal], rally_windows: list[RallySegmentWindow]
) -> int:
    if not signals:
        return 0

    def in_rally_window(timestamp_s: float) -> bool:
        return any(
            window.start_time_s <= timestamp_s <= window.end_time_s
            for window in rally_windows
        )

    return sum(1 for signal in signals if _is_dead_time(signal) or not in_rally_window(signal.timestamp_s))


def _resolve_video_seconds_total(
    signals: list[FrameSignal],
    *,
    rally_windows: list[RallySegmentWindow],
    fallback: float | None,
) -> float:
    if fallback is not None:
        return max(0.0, fallback)

    if not signals:
        return 0.0

    last_timestamp = max(signal.timestamp_s for signal in signals)
    first_timestamp = min(signal.timestamp_s for signal in signals)
    estimated_step = _estimate_step_seconds(signals)
    return max(0.0, last_timestamp - first_timestamp + estimated_step)


def _resolve_sampled_fps(
    signals: list[FrameSignal], *, fallback: float | None
) -> float:
    if fallback is not None:
        return max(0.01, fallback)

    step_seconds = _estimate_step_seconds(signals)
    if step_seconds <= 0:
        return 1.0
    return round(1.0 / step_seconds, 3)


def _estimate_step_seconds(signals: list[FrameSignal]) -> float:
    if len(signals) < 2:
        return 1.0

    deltas = [
        current.timestamp_s - previous.timestamp_s
        for previous, current in zip(signals, signals[1:])
        if current.timestamp_s > previous.timestamp_s
    ]
    if not deltas:
        return 1.0

    return max(0.001, median(deltas))
