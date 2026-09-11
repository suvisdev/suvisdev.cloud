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
        from viewer.adapter.inbound.api.v1.avatar_router import avatar_router
        from viewer.adapter.inbound.api.v1.oauth_router import oauth_router
        from viewer.adapter.inbound.api.v1.profile_router import profile_router

        router = APIRouter(prefix="/viewer", tags=["viewer"])
        # login/signup 라우터는 2026-09-11 언마운트 — 프론트·susu 실사용은 auth
        # 게이트웨이(/auth/login·/auth/signup)이고(호출처 grep 0건 실측), 이
        # 경로는 비밀번호 검증 오라클로만 노출돼 있었다. 코드 자체는 롤백
        # 대비로 보존.
        router.include_router(oauth_router)
        router.include_router(profile_router)
        router.include_router(avatar_router)
        router.include_router(admin_agents_router)
        router.include_router(admin_users_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
