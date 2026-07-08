"""랭킹 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_rankings_dto import RankingListDto


class RankingsUseCase(ABC):
    @abstractmethod
    async def get_hot(self, source: str, limit: int) -> RankingListDto:
        pass


class GenerateChatTrendRankingUseCase(ABC):
    @abstractmethod
    async def execute(self, days: int, limit: int) -> int:
        """chat_trend 랭킹을 집계·스냅샷 저장하고 저장 건수를 반환한다."""
