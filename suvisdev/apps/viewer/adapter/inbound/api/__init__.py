from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["viewer_router"]


def __getattr__(name: str) -> APIRouter:
    if name == "viewer_router":
        from fastapi import APIRouter

        from viewer.adapter.inbound.api.v1.login_router import login_router
        from viewer.adapter.inbound.api.v1.signup_router import signup_router

        router = APIRouter(prefix="/viewer", tags=["viewer"])
        router.include_router(login_router)
        router.include_router(signup_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
