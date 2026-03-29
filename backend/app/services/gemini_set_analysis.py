from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from backend.app.integrations.gemini_client import GeminiClient, GeminiVideoSource
from backend.app.schemas.gemini_analysis import GeminiSetAnalysis
from backend.app.schemas.preprocessing import CandidateClip


@dataclass(frozen=True, slots=True)
class GeminiSetAnalysisBatchResult:
    analyses: list[GeminiSetAnalysis]
    low_confidence_candidate_clips: list[str]


class GeminiSetAnalysisService:
    def __init__(
        self,
        *,
        client: GeminiClient | None = None,
        minimum_candidate_confidence: float = 0.5,
    ) -> None:
        self._client = client or GeminiClient()
        self._minimum_candidate_confidence = minimum_candidate_confidence

    def analyze_candidate_clip(
        self,
        candidate_clip: CandidateClip,
        *,
        raw_response: Mapping[str, object] | GeminiSetAnalysis | None = None,
        video_source: GeminiVideoSource | None = None,
    ) -> GeminiSetAnalysis:
        analysis = self._client.analyze_candidate_clip(
            candidate_clip,
            raw_response=raw_response,
            video_source=video_source,
        )
        return self._apply_candidate_confidence(candidate_clip, analysis)

    def analyze_candidate_clips(
        self,
        candidate_clips: list[CandidateClip],
        *,
        raw_responses: Mapping[str, Mapping[str, object] | GeminiSetAnalysis] | None = None,
        video_source: GeminiVideoSource | None = None,
    ) -> GeminiSetAnalysisBatchResult:
        analyses: list[GeminiSetAnalysis] = []
        low_confidence_candidate_clips: list[str] = []

        for candidate_clip in candidate_clips:
            raw_response = None
            if raw_responses is not None:
                raw_response = raw_responses.get(candidate_clip.candidate_clip_id)

            analysis = self.analyze_candidate_clip(
                candidate_clip,
                raw_response=raw_response,
                video_source=video_source,
            )
            analyses.append(analysis)

            if candidate_clip.confidence < self._minimum_candidate_confidence:
                low_confidence_candidate_clips.append(candidate_clip.candidate_clip_id)

        return GeminiSetAnalysisBatchResult(
            analyses=analyses,
            low_confidence_candidate_clips=low_confidence_candidate_clips,
        )

    def _apply_candidate_confidence(
        self,
        candidate_clip: CandidateClip,
        analysis: GeminiSetAnalysis,
    ) -> GeminiSetAnalysis:
        if candidate_clip.confidence >= self._minimum_candidate_confidence:
            return analysis

        notes = "candidate clip confidence below threshold"
        if analysis.notes:
            notes = f"{analysis.notes}; {notes}"

        return analysis.model_copy(
            update={
                "confidence": min(analysis.confidence, candidate_clip.confidence),
                "notes": notes,
            }
        )


def analyze_candidate_clips(
    candidate_clips: list[CandidateClip],
    *,
    raw_responses: Mapping[str, Mapping[str, object] | GeminiSetAnalysis] | None = None,
    client: GeminiClient | None = None,
    video_source: GeminiVideoSource | None = None,
    minimum_candidate_confidence: float = 0.5,
) -> GeminiSetAnalysisBatchResult:
    service = GeminiSetAnalysisService(
        client=client,
        minimum_candidate_confidence=minimum_candidate_confidence,
    )
    return service.analyze_candidate_clips(
        candidate_clips,
        raw_responses=raw_responses,
        video_source=video_source,
    )
