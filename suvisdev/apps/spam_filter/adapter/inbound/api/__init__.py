from __future__ import annotations

from fastapi import APIRouter

__all__ = ["spam_filter_router"]


def __getattr__(name: str) -> APIRouter:
    if name == "spam_filter_router":
        from spam_filter.adapter.inbound.api.v1.spam_router import spam_router

        router = APIRouter(prefix="/spam-filter", tags=["spam-filter"])
        router.include_router(spam_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
