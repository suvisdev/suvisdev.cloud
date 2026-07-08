from __future__ import annotations

from fastapi import APIRouter

__all__ = ["mova_router"]


def __getattr__(name: str) -> APIRouter:
    if name == "mova_router":
        from fastapi import APIRouter

        from mova.adapter.inbound.api.v1.collections_router import collections_router
        from mova.adapter.inbound.api.v1.market_watchlist_router import market_watchlist_router
        from mova.adapter.inbound.api.v1.mypage_router import mypage_router
        from mova.adapter.inbound.api.v1.import_router import import_router
        from mova.adapter.inbound.api.v1.market_chat_router import market_chat_router
        from mova.adapter.inbound.api.v1.market_picks_router import market_picks_router
        from mova.adapter.inbound.api.v1.market_rankings_router import market_rankings_router
        from mova.adapter.inbound.api.v1.market_reviews_router import market_reviews_router
        from mova.adapter.inbound.api.v1.platform_assistants_router import (
            platform_assistants_router,
        )
        from mova.adapter.inbound.api.v1.studio_actors_router import studio_actors_router
        from mova.adapter.inbound.api.v1.studio_characters_router import studio_characters_router
        from mova.adapter.inbound.api.v1.studio_movies_router import studio_movies_router
        from mova.adapter.inbound.api.v1.studio_search_router import studio_search_router
        from mova.adapter.inbound.api.v1.studio_tags_router import studio_tags_router

        router = APIRouter(prefix="/mova", tags=["mova"])
        router.include_router(studio_movies_router)
        router.include_router(studio_actors_router)
        router.include_router(studio_characters_router)
        router.include_router(studio_tags_router)
        router.include_router(import_router)
        router.include_router(studio_search_router)
        router.include_router(market_rankings_router)
        router.include_router(market_chat_router)
        router.include_router(market_picks_router)
        router.include_router(market_reviews_router)
        router.include_router(platform_assistants_router)
        router.include_router(collections_router)
        router.include_router(market_watchlist_router)
        router.include_router(mypage_router)
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
