from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import (
    ProcessingStage,
    RulesetVariant,
    VideoAssetStatus,
    VideoSourceType,
)


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class AssetPlaceholder(APIModel):
    kind: Literal["normalized", "proxy"]
    path: str
    status: VideoAssetStatus
    format: str = "mp4"
    codec: str = "h264"
    duration_seconds: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None


class VideoJobSummary(APIModel):
    id: str
    job_id: str
    title: str
    source_type: VideoSourceType
    source_url: str | None = None
    local_path: str | None = None
    mime_type: str | None = None
    source_file_name: str | None = None
    ruleset_variant: RulesetVariant
    status: ProcessingStage
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str
    normalized_asset: AssetPlaceholder
    proxy_asset: AssetPlaceholder
    created_at: datetime | None = None
    updated_at: datetime | None = None
