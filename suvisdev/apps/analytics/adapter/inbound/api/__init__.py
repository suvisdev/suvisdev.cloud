from __future__ import annotations

from fastapi import APIRouter

__all__ = ["analytics_router"]


def __getattr__(name: str) -> APIRouter:
    if name == "analytics_router":
        from analytics.adapter.inbound.api.v1.visitor_router import visitor_router

        router = APIRouter(prefix="/analytics", tags=["analytics"])
        router.include_router(visitor_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
