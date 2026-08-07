from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.market_watchlist_schema import (
    WatchlistAddSchema,
    WatchlistSchema,
)
from mova.app.ports.input.market_watchlist_use_case import WatchlistUseCase
from mova.dependencies.market_watchlist_provider import get_watchlist_use_case
from shared.security.require_user import UserPrincipal, require_user

market_watchlist_router = APIRouter(prefix="/watchlist", tags=["mova-watchlist"])


class _CheckResponse(BaseModel):
    in_watchlist: bool


def _assert_self(principal: UserPrincipal, user_id: int) -> None:
    """찜 목록은 개인 데이터다 — 2026-08-07 이전엔 가드가 없어 user_id만 알면
    남의 목록을 읽는 것은 물론 **추가·삭제까지** 가능했다."""
    if principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인 찜 목록만 다룰 수 있습니다.")


@market_watchlist_router.get("/{user_id}", response_model=WatchlistSchema)
async def get_watchlist(
    user_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> WatchlistSchema:
    _assert_self(principal, user_id)
    return (await use_case.get_watchlist(user_id)).to_schema()


@market_watchlist_router.get("/{user_id}/check/{movie_id}", response_model=_CheckResponse)
async def check_watchlist(
    user_id: int,
    movie_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> _CheckResponse:
    _assert_self(principal, user_id)
    result = await use_case.is_in_watchlist(user_id, movie_id)
    return _CheckResponse(in_watchlist=result)


@market_watchlist_router.post("", status_code=201)
async def add_to_watchlist(
    body: WatchlistAddSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> dict[str, str]:
    _assert_self(principal, body.user_id)
    await use_case.add(body.user_id, body.movie_id)
    return {"status": "added"}


@market_watchlist_router.delete("/{user_id}/{movie_id}", status_code=200)
async def remove_from_watchlist(
    user_id: int,
    movie_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> dict[str, str]:
    _assert_self(principal, user_id)
    await use_case.remove(user_id, movie_id)
    return {"status": "removed"}
