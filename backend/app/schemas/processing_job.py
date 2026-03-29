from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.app.schemas.common import ProcessingStage


class ProcessingJob(BaseModel):
    job_id: str
    video_asset_id: str
    stage: ProcessingStage
    progress: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    error_message: str | None = None


class ProcessingJobUpdate(BaseModel):
    stage: ProcessingStage | None = None
    progress: float | None = None
    error_message: str | None = None

