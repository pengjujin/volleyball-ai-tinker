from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.common import RulesetVariant, VideoAssetStatus, VideoSourceType


class VideoAsset(BaseModel):
    video_asset_id: str
    source_type: VideoSourceType
    source_url: str | None = None
    local_path: str | None = None
    mime_type: str | None = None
    duration_seconds: float | None = None
    fps: float | None = None
    ruleset_variant: RulesetVariant
    status: VideoAssetStatus = VideoAssetStatus.uploaded
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VideoAssetCreate(BaseModel):
    source_type: VideoSourceType
    source_url: str | None = None
    local_path: str | None = None
    mime_type: str | None = None
    ruleset_variant: RulesetVariant
    duration_seconds: float | None = None
    fps: float | None = None


class VideoAssetSummary(BaseModel):
    video_asset_id: str
    ruleset_variant: RulesetVariant
    status: VideoAssetStatus
    source_type: VideoSourceType
