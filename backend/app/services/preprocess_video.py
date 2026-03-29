from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.app.schemas.preprocessing import CandidateClip, FrameSignal, PreprocessingSummary
from backend.app.schemas.rally_segment import RallySegmentWindow
from backend.app.services.candidate_set_proposal import (
    estimate_video_reduction,
    propose_candidate_set_clips,
)
from backend.app.services.rally_segmentation import detect_rally_windows


@dataclass(frozen=True, slots=True)
class PreprocessVideoResult:
    rally_windows: list[RallySegmentWindow]
    candidate_clips: list[CandidateClip]
    summary: PreprocessingSummary
    reduction_estimate: float


def preprocess_video_signals(
    *,
    video_asset_id: str,
    frame_signals: Sequence[FrameSignal],
    sampled_fps: float,
) -> PreprocessVideoResult:
    ordered_signals = sorted(frame_signals, key=lambda signal: signal.timestamp_s)
    rally_windows = detect_rally_windows(ordered_signals)
    candidate_result = propose_candidate_set_clips(
        video_asset_id=video_asset_id,
        frame_signals=list(ordered_signals),
        rally_windows=list(rally_windows),
        sampled_fps=sampled_fps,
    )
    reduction_estimate = estimate_video_reduction(candidate_result.summary)
    return PreprocessVideoResult(
        rally_windows=rally_windows,
        candidate_clips=candidate_result.candidate_clips,
        summary=candidate_result.summary,
        reduction_estimate=reduction_estimate,
    )
