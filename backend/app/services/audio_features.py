from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from backend.app.schemas.preprocessing import FrameSignal


@dataclass(frozen=True, slots=True)
class AudioBurst:
    start_time_s: float
    peak_time_s: float
    end_time_s: float
    peak_score: float

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_time_s - self.start_time_s)


def detect_audio_bursts(
    frame_signals: Sequence[FrameSignal],
    *,
    threshold: float = 0.62,
    min_gap_s: float = 0.75,
    min_duration_s: float = 0.2,
) -> list[AudioBurst]:
    """Group sustained audio spikes into deterministic contact bursts."""

    if not frame_signals:
        return []

    ordered = sorted(frame_signals, key=lambda signal: signal.timestamp_s)
    bursts: list[AudioBurst] = []

    current_start: float | None = None
    current_end: float | None = None
    peak_time = 0.0
    peak_score = 0.0
    last_above_threshold: float | None = None

    for signal in ordered:
        score = signal.audio_energy_score
        if score >= threshold:
            if current_start is None:
                current_start = signal.timestamp_s
                peak_time = signal.timestamp_s
                peak_score = score
            elif current_end is not None and signal.timestamp_s - current_end > min_gap_s:
                _append_burst(
                    bursts,
                    start_time_s=current_start,
                    peak_time_s=peak_time,
                    end_time_s=current_end,
                    peak_score=peak_score,
                    min_duration_s=min_duration_s,
                )
                current_start = signal.timestamp_s
                peak_time = signal.timestamp_s
                peak_score = score

            if score >= peak_score:
                peak_time = signal.timestamp_s
                peak_score = score

            current_end = signal.timestamp_s
            last_above_threshold = signal.timestamp_s
            continue

        if current_start is not None and last_above_threshold is not None:
            if signal.timestamp_s - last_above_threshold <= min_gap_s:
                current_end = signal.timestamp_s
                continue

            _append_burst(
                bursts,
                start_time_s=current_start,
                peak_time_s=peak_time,
                end_time_s=current_end if current_end is not None else last_above_threshold,
                peak_score=peak_score,
                min_duration_s=min_duration_s,
            )
            current_start = None
            current_end = None
            peak_time = 0.0
            peak_score = 0.0
            last_above_threshold = None

    if current_start is not None:
        _append_burst(
            bursts,
            start_time_s=current_start,
            peak_time_s=peak_time,
            end_time_s=current_end if current_end is not None else current_start,
            peak_score=peak_score,
            min_duration_s=min_duration_s,
        )

    return bursts


def in_audio_burst(timestamp_s: float, bursts: Iterable[AudioBurst]) -> bool:
    return any(burst.start_time_s <= timestamp_s <= burst.end_time_s for burst in bursts)


def burst_peak_score(timestamp_s: float, bursts: Iterable[AudioBurst]) -> float:
    for burst in bursts:
        if burst.start_time_s <= timestamp_s <= burst.end_time_s:
            return burst.peak_score
    return 0.0


def _append_burst(
    bursts: list[AudioBurst],
    *,
    start_time_s: float,
    peak_time_s: float,
    end_time_s: float,
    peak_score: float,
    min_duration_s: float,
) -> None:
    if end_time_s < start_time_s:
        end_time_s = start_time_s

    if end_time_s - start_time_s < min_duration_s:
        end_time_s = start_time_s + min_duration_s

    bursts.append(
        AudioBurst(
            start_time_s=start_time_s,
            peak_time_s=peak_time_s,
            end_time_s=end_time_s,
            peak_score=peak_score,
        )
    )
