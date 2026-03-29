from .health import router as health_router
from .info import router as info_router
from .videos import router as videos_router

__all__ = ["health_router", "info_router", "videos_router"]
