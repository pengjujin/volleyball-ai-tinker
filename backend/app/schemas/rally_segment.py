from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RallySegment(BaseModel):
    rally_segment_id: str
    video_asset_id: str
    start_time_s: float
    end_time_s: float
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime | None = None


class RallySegmentWindow(BaseModel):
    start_time_s: float
    end_time_s: float
    confidence: float = Field(ge=0.0, le=1.0)

