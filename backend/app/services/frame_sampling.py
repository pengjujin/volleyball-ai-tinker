from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from backend.app.schemas.preprocessing import FrameSignal

_MOTION_WEIGHT = 0.42
_BALL_WEIGHT = 0.28
_AUDIO_WEIGHT = 0.20
_COURT_WEIGHT = 0.10
_SCENE_CUT_PENALTY = 0.40
_REPLAY_PENALTY = 0.30
_CROWD_PENALTY = 0.25
_ACTIVE_THRESHOLD = 0.45


@dataclass(frozen=True)
class FrameSamplingResult:
    sampled_frames: list[FrameSignal]
    filtered_frames: int


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_frame_activity(signal: FrameSignal) -> float:
    score = (
        (_MOTION_WEIGHT * signal.motion_score)
        + (_BALL_WEIGHT * signal.ball_motion_score)
        + (_AUDIO_WEIGHT * signal.audio_energy_score)
        + (_COURT_WEIGHT * signal.on_court_score)
    )

    if signal.scene_cut:
        score -= _SCENE_CUT_PENALTY
    if signal.replay_like:
        score -= _REPLAY_PENALTY
    if signal.crowd_like:
        score -= _CROWD_PENALTY

    if signal.ball_motion_score >= 0.7:
        score += 0.10
    if signal.audio_energy_score >= 0.8:
        score += 0.05

    return clamp_score(score)


def is_active_frame(signal: FrameSignal, *, activity_threshold: float = _ACTIVE_THRESHOLD) -> bool:
    score = score_frame_activity(signal)
    if signal.scene_cut or signal.replay_like or signal.crowd_like:
        if score < activity_threshold + 0.08:
            return False

    return (
        score >= activity_threshold
        or signal.ball_motion_score >= 0.60
        or (
            signal.motion_score >= 0.65
            and signal.audio_energy_score >= 0.35
            and signal.on_court_score >= 0.70
        )
    )


def filter_dead_time_frames(
    frame_signals: Sequence[FrameSignal],
    *,
    activity_threshold: float = _ACTIVE_THRESHOLD,
) -> list[FrameSignal]:
    return [
        signal
        for signal in frame_signals
        if is_active_frame(signal, activity_threshold=activity_threshold)
    ]


def summarize_activity(frame_signals: Sequence[FrameSignal]) -> float:
    if not frame_signals:
        return 0.0
    return mean(score_frame_activity(signal) for signal in frame_signals)

