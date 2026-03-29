from __future__ import annotations

from enum import Enum


class RulesetVariant(str, Enum):
    six_player = "6-player"
    nine_man = "9-man"


class TeamSide(str, Enum):
    near_side = "near_side"
    far_side = "far_side"
    unknown = "unknown"


class ProcessingStage(str, Enum):
    queued = "queued"
    running = "running"
    failed = "failed"
    completed = "completed"


class SetTempo(str, Enum):
    quick = "quick"
    medium = "medium"
    high_slow = "high/slow"


class VideoSourceType(str, Enum):
    local_path = "local_path"
    upload = "upload"
    youtube = "youtube"


class VideoAssetStatus(str, Enum):
    uploaded = "uploaded"
    normalizing = "normalizing"
    ready = "ready"
    failed = "failed"
