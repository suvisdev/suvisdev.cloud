from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.market_watchlist_schema import (
    WatchlistAddSchema,
    WatchlistSchema,
)
from mova.app.ports.input.market_watchlist_use_case import WatchlistUseCase
from mova.dependencies.market_watchlist_provider import get_watchlist_use_case

market_watchlist_router = APIRouter(prefix="/watchlist", tags=["mova-watchlist"])


class _CheckResponse(BaseModel):
    in_watchlist: bool


@market_watchlist_router.get("/{user_id}", response_model=WatchlistSchema)
async def get_watchlist(
    user_id: int,
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> WatchlistSchema:
    return (await use_case.get_watchlist(user_id)).to_schema()


@market_watchlist_router.get("/{user_id}/check/{movie_id}", response_model=_CheckResponse)
async def check_watchlist(
    user_id: int,
    movie_id: int,
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> _CheckResponse:
    result = await use_case.is_in_watchlist(user_id, movie_id)
    return _CheckResponse(in_watchlist=result)


@market_watchlist_router.post("", status_code=201)
async def add_to_watchlist(
    body: WatchlistAddSchema,
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> dict[str, str]:
    await use_case.add(body.user_id, body.movie_id)
    return {"status": "added"}


@market_watchlist_router.delete("/{user_id}/{movie_id}", status_code=200)
async def remove_from_watchlist(
    user_id: int,
    movie_id: int,
    use_case: WatchlistUseCase = Depends(get_watchlist_use_case),
) -> dict[str, str]:
    await use_case.remove(user_id, movie_id)
    return {"status": "removed"}
