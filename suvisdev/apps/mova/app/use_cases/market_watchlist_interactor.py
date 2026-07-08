from __future__ import annotations

from mova.app.dtos.market_watchlist_dto import WatchlistDto
from mova.app.ports.input.market_watchlist_use_case import WatchlistUseCase
from mova.app.ports.output.market_watchlist_repository import WatchlistRepository


class WatchlistInteractor(WatchlistUseCase):
    def __init__(self, repository: WatchlistRepository) -> None:
        self._repository = repository

    async def get_watchlist(self, user_id: int) -> WatchlistDto:
        return await self._repository.get_watchlist(user_id)

    async def add(self, user_id: int, movie_id: int) -> None:
        await self._repository.add(user_id, movie_id)

    async def remove(self, user_id: int, movie_id: int) -> None:
        await self._repository.remove(user_id, movie_id)

    async def is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        return await self._repository.is_in_watchlist(user_id, movie_id)
