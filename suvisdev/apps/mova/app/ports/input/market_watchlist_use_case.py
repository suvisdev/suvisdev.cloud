from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_watchlist_dto import WatchlistDto


class WatchlistUseCase(ABC):
    @abstractmethod
    async def get_watchlist(self, user_id: int) -> WatchlistDto:
        pass

    @abstractmethod
    async def add(self, user_id: int, movie_id: int) -> None:
        pass

    @abstractmethod
    async def remove(self, user_id: int, movie_id: int) -> None:
        pass

    @abstractmethod
    async def is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        pass
