from __future__ import annotations

from backend.app._compat import APIRouter

router = APIRouter(tags=["health"])


def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health")
def health_endpoint() -> dict[str, str]:
    return health_check()

