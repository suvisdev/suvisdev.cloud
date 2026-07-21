from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["viewer_router"]


def __getattr__(name: str) -> APIRouter:
    if name == "viewer_router":
        from fastapi import APIRouter

        from viewer.adapter.inbound.api.v1.admin_agents_router import admin_agents_router
        from viewer.adapter.inbound.api.v1.admin_users_router import admin_users_router
        from viewer.adapter.inbound.api.v1.login_router import login_router
        from viewer.adapter.inbound.api.v1.oauth_router import oauth_router
        from viewer.adapter.inbound.api.v1.profile_router import profile_router
        from viewer.adapter.inbound.api.v1.signup_router import signup_router

        router = APIRouter(prefix="/viewer", tags=["viewer"])
        router.include_router(login_router)
        router.include_router(signup_router)
        router.include_router(oauth_router)
        router.include_router(profile_router)
        router.include_router(admin_agents_router)
        router.include_router(admin_users_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
