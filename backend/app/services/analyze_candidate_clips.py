from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from backend.app.integrations.gemini_client import GeminiClient, GeminiVideoSource
from backend.app.schemas.gemini_analysis import GeminiSetAnalysis
from backend.app.schemas.preprocessing import CandidateClip
from backend.app.schemas.set_event import SetEvent
from backend.app.services.event_normalization import normalize_gemini_set_analyses
from backend.app.services.gemini_set_analysis import analyze_candidate_clips


@dataclass(frozen=True, slots=True)
class CandidateClipEventResult:
    analyses: list[GeminiSetAnalysis]
    set_events: list[SetEvent]
    low_confidence_candidate_clips: list[str]


def analyze_candidate_clips_to_events(
    *,
    video_asset_id: str,
    candidate_clips: list[CandidateClip],
    raw_responses: Mapping[str, Mapping[str, object] | GeminiSetAnalysis] | None = None,
    client: GeminiClient | None = None,
    video_source: GeminiVideoSource | None = None,
    minimum_candidate_confidence: float = 0.5,
) -> CandidateClipEventResult:
    analysis_result = analyze_candidate_clips(
        candidate_clips,
        raw_responses=raw_responses,
        client=client,
        video_source=video_source,
        minimum_candidate_confidence=minimum_candidate_confidence,
    )
    set_events = normalize_gemini_set_analyses(
        analysis_result.analyses,
        video_asset_id=video_asset_id,
    )
    return CandidateClipEventResult(
        analyses=analysis_result.analyses,
        set_events=set_events,
        low_confidence_candidate_clips=analysis_result.low_confidence_candidate_clips,
    )
