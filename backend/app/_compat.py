from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Iterable

try:  # pragma: no cover - exercised when FastAPI is installed locally.
    from fastapi import APIRouter as _FastAPIRouter
    from fastapi import FastAPI as _FastAPI
except Exception:  # pragma: no cover - fallback used in this workspace.
    _FastAPIRouter = None
    _FastAPI = None


@dataclass(frozen=True)
class RouteInfo:
    path: str
    methods: tuple[str, ...]
    endpoint: Callable[..., Any]
    name: str


class _FallbackRouter:
    def __init__(self, prefix: str = "", tags: Iterable[str] | None = None) -> None:
        self.prefix = prefix
        self.tags = list(tags or [])
        self.routes: list[RouteInfo] = []

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: Iterable[str],
        name: str | None = None,
    ) -> Callable[..., Any]:
        route = RouteInfo(
            path=f"{self.prefix}{path}",
            methods=tuple(method.upper() for method in methods),
            endpoint=endpoint,
            name=name or endpoint.__name__,
        )
        self.routes.append(route)
        return endpoint

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._decorator(path, ("GET",), **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._decorator(path, ("POST",), **kwargs)

    def _decorator(
        self,
        path: str,
        methods: Iterable[str],
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def wrapper(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, endpoint, methods, kwargs.get("name"))
            return endpoint

        return wrapper


class _FallbackFastAPI(_FallbackRouter):
    def __init__(self, title: str, version: str, description: str = "") -> None:
        super().__init__()
        self.title = title
        self.version = version
        self.description = description
        self.state = SimpleNamespace()

    def include_router(self, router: Any) -> None:
        routes = getattr(router, "routes", [])
        self.routes.extend(routes)

    def openapi(self) -> dict[str, Any]:
        return {
            "openapi": "3.1.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": {
                route.path: {"methods": list(route.methods), "name": route.name}
                for route in self.routes
            },
        }


def APIRouter(*args: Any, **kwargs: Any) -> Any:
    if _FastAPIRouter is not None:
        return _FastAPIRouter(*args, **kwargs)
    return _FallbackRouter(*args, **kwargs)


def FastAPI(*args: Any, **kwargs: Any) -> Any:
    if _FastAPI is not None:
        return _FastAPI(*args, **kwargs)
    return _FallbackFastAPI(*args, **kwargs)


def get_registered_routes(app: Any) -> list[RouteInfo]:
    routes = getattr(app, "routes", [])
    normalized: list[RouteInfo] = []

    for route in routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        endpoint = getattr(route, "endpoint", None)
        name = getattr(route, "name", None) or getattr(endpoint, "__name__", "unknown")
        if path and methods and endpoint:
            normalized.append(
                RouteInfo(
                    path=path,
                    methods=tuple(sorted(method.upper() for method in methods)),
                    endpoint=endpoint,
                    name=name,
                )
            )

    return normalized

