from __future__ import annotations

from backend.app._compat import APIRouter
from backend.app.config import get_settings

router = APIRouter(tags=["info"])


def get_app_info() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": "true" if settings.debug else "false",
        "default_ruleset_variant": settings.default_ruleset_variant,
    }


@router.get("/info")
def info_endpoint() -> dict[str, str]:
    return get_app_info()

