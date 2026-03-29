from __future__ import annotations

import logging
from email.parser import BytesParser
from email.policy import default
from urllib.parse import parse_qs

from fastapi import HTTPException, Request, status

from backend.app._compat import APIRouter
from backend.app.schemas.common import RulesetVariant, VideoSourceType
from backend.app.schemas.analytics import MatchAnalyticsSummary
from backend.app.schemas.set_event import SetEvent
from backend.app.schemas.video_ingest import VideoJobSummary
from backend.app.services.video_registry import (
    VideoSubmissionError,
    get_video_registry,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])
logger = logging.getLogger("volleyball_ai.api.videos")


@router.post("", response_model=VideoJobSummary, status_code=status.HTTP_201_CREATED)
async def create_video_endpoint(request: Request) -> VideoJobSummary:
    registry = get_video_registry()
    submission = await _parse_submission(request)
    logger.info(
        "Received video submission | title=%s | source_type=%s | ruleset=%s | source_url=%s | local_path=%s | file_name=%s | mime_type=%s | file_bytes=%s",
        submission["title"],
        submission["source_type"],
        submission["ruleset_variant"],
        submission["source_url"],
        submission["local_path"],
        submission["source_file_name"],
        submission["source_mime_type"],
        len(submission["source_file_bytes"]) if isinstance(submission["source_file_bytes"], bytes) else 0,
    )

    try:
        summary = registry.create_video(
            title=submission["title"],
            source_type=submission["source_type"],
            ruleset_variant=submission["ruleset_variant"],
            source_url=submission["source_url"],
            local_path=submission["local_path"],
            source_file_name=submission["source_file_name"],
            source_file_bytes=submission["source_file_bytes"],
            source_mime_type=submission["source_mime_type"],
        )
        logger.info(
            "Created video job | video_id=%s | job_id=%s | status=%s | progress=%.2f",
            summary.id,
            summary.job_id,
            summary.status,
            summary.progress,
        )
        registry.start_processing(summary.id)
        logger.info("Background processing launched | video_id=%s", summary.id)
        return summary
    except VideoSubmissionError as exc:
        logger.exception("Video submission failed validation")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{video_asset_id}", response_model=VideoJobSummary)
def get_video_endpoint(video_asset_id: str) -> VideoJobSummary:
    registry = get_video_registry()
    summary = registry.get_video(video_asset_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
    logger.info(
        "Video job status requested | video_id=%s | status=%s | progress=%.2f | message=%s",
        video_asset_id,
        summary.status,
        summary.progress,
        summary.message,
    )
    return summary


@router.get("/{video_asset_id}/events", response_model=list[SetEvent])
def get_video_events_endpoint(video_asset_id: str) -> list[SetEvent]:
    registry = get_video_registry()
    events = registry.get_events(video_asset_id)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
    logger.info(
        "Video events requested | video_id=%s | count=%s",
        video_asset_id,
        len(events),
    )
    return events


@router.get("/{video_asset_id}/analytics", response_model=MatchAnalyticsSummary)
def get_video_analytics_endpoint(video_asset_id: str) -> MatchAnalyticsSummary:
    registry = get_video_registry()
    analytics = registry.get_analytics(video_asset_id)
    if analytics is None:
        summary = registry.get_video(video_asset_id)
        if summary is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
        logger.info(
            "Video analytics requested before ready | video_id=%s | status=%s | progress=%.2f",
            video_asset_id,
            summary.status,
            summary.progress,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analytics are not ready yet.",
        )
    logger.info("Video analytics requested | video_id=%s", video_asset_id)
    return analytics


async def _parse_submission(request: Request) -> dict[str, object]:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        payload = await request.json()
        return _normalize_payload(payload)

    body = await request.body()

    if "multipart/form-data" in content_type:
        payload: dict[str, object] = {}
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
            + body
        )

        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue

            filename = part.get_filename()
            if filename:
                payload["sourceFileName"] = filename
                payload["sourceFileBytes"] = part.get_payload(decode=True)
                payload["sourceMimeType"] = part.get_content_type()
                continue

            text = part.get_payload(decode=True)
            payload[name] = text.decode("utf-8") if text is not None else ""

        return _normalize_payload(payload)

    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(body.decode("utf-8"))
        payload = {
            "title": _first_value(parsed, "title"),
            "sourceType": _first_value(parsed, "sourceType"),
            "sourceUrl": _first_value(parsed, "sourceUrl"),
            "localPath": _first_value(parsed, "localPath"),
            "rulesetVariant": _first_value(parsed, "rulesetVariant"),
        }
        return _normalize_payload(payload)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Unsupported content type for video submission.",
    )


def _normalize_payload(payload: dict[str, object]) -> dict[str, object]:
    source_type_raw = _first_present(payload, "sourceType", "source_type")
    ruleset_variant_raw = _first_present(payload, "rulesetVariant", "ruleset_variant")
    source_url = _first_present(payload, "sourceUrl", "source_url")
    local_path = _first_present(payload, "localPath", "local_path")
    source_file_name = _first_present(payload, "sourceFileName", "source_file_name")
    source_file_bytes = _first_present(payload, "sourceFileBytes", "source_file_bytes")
    source_mime_type = _first_present(payload, "sourceMimeType", "source_mime_type")
    title = _first_present(payload, "title") or ""

    if source_type_raw is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="sourceType is required.")

    if ruleset_variant_raw is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="rulesetVariant is required.")

    return {
        "title": str(title),
        "source_type": VideoSourceType(_coerce_value(source_type_raw)),
        "source_url": str(source_url) if source_url else None,
        "local_path": str(local_path) if local_path else None,
        "source_file_name": str(source_file_name) if source_file_name else None,
        "source_file_bytes": source_file_bytes if isinstance(source_file_bytes, bytes) else None,
        "source_mime_type": str(source_mime_type) if source_mime_type else None,
        "ruleset_variant": RulesetVariant(_coerce_value(ruleset_variant_raw)),
    }


def _first_value(mapping: dict[str, list[str]], key: str) -> str | None:
    values = mapping.get(key)
    if not values:
        return None
    return values[0]


def _first_present(payload: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _coerce_value(value: object) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value)
