from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FrameSignal(BaseModel):
    timestamp_s: float = Field(ge=0.0)
    motion_score: float = Field(ge=0.0, le=1.0)
    ball_motion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    on_court_score: float = Field(default=1.0, ge=0.0, le=1.0)
    audio_energy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    scene_cut: bool = False
    replay_like: bool = False
    crowd_like: bool = False


class CandidateClip(BaseModel):
    candidate_clip_id: str
    video_asset_id: str
    rally_segment_id: str | None = None
    start_time_s: float = Field(ge=0.0)
    end_time_s: float = Field(gt=0.0)
    trigger_label: str
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime | None = None


class PreprocessingSummary(BaseModel):
    video_asset_id: str
    sampled_fps: float = Field(gt=0.0)
    total_frames_sampled: int = Field(ge=0)
    dead_time_frames_filtered: int = Field(ge=0)
    rally_segments_detected: int = Field(ge=0)
    candidate_clips_detected: int = Field(ge=0)
    candidate_seconds_total: float = Field(ge=0.0)
    video_seconds_total: float = Field(ge=0.0)

