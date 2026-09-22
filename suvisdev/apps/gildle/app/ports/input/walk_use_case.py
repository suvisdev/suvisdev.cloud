from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.app.dtos.walk_dto import (
    WalkCreateCommand,
    WalkListQuery,
    WalkStats,
    WalkSummary,
)
from gildle.domain.entities.walk_entity import Walk


class WalkUseCase(ABC):
    """산책 기록 입력 포트."""

    @abstractmethod
    async def record(self, command: WalkCreateCommand) -> Walk: ...

    @abstractmethod
    async def list_mine(self, query: WalkListQuery) -> list[WalkSummary]: ...

    @abstractmethod
    async def detail(self, walk_id: int, user_id: int) -> Walk:
        """남의 기록은 볼 수 없다 — 소유자가 아니면 404로 막는다."""
        ...

    @abstractmethod
    async def remove(self, walk_id: int, user_id: int) -> None: ...

    @abstractmethod
    async def stats(self, user_id: int) -> WalkStats: ...
