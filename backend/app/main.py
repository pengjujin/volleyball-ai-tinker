from __future__ import annotations

import logging

from backend.app._compat import FastAPI
from backend.app.api import health_router, info_router, videos_router
from backend.app.config import get_settings


_LOGGING_CONFIGURED = False


def _configure_logging() -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    _LOGGING_CONFIGURED = True


def create_app() -> object:
    _configure_logging()
    settings = get_settings()
    logger = logging.getLogger("volleyball_ai.app")
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Volleyball AI backend scaffold",
    )
    app.include_router(health_router)
    app.include_router(info_router)
    app.include_router(videos_router)
    logger.info(
        "Backend app created | version=%s | storage_root=%s | gemini_live_enabled=%s | gemini_model=%s",
        settings.app_version,
        settings.storage_root,
        settings.gemini_live_enabled,
        settings.gemini_model,
    )
    return app


app = create_app()
