from __future__ import annotations

from fastapi import APIRouter

__all__ = ["contents_router"]


def __getattr__(name: str) -> APIRouter:
    if name == "contents_router":
        from contents.adapter.inbound.api.v1.soccer_chat_router import soccer_chat_router

        router = APIRouter(prefix="/contents", tags=["contents"])
        router.include_router(soccer_chat_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
