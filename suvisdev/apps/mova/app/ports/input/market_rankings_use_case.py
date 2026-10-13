"""랭킹 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_rankings_dto import RankingListDto


class RankingsUseCase(ABC):
    @abstractmethod
    async def get_hot(self, source: str, limit: int) -> RankingListDto:
        pass

    @abstractmethod
    async def record_view(
        self,
        movie_id: int,
        *,
        user_id: int | None,
        visitor_id: str | None,
        user_agent: str | None,
    ) -> bool:
        """영화 상세 열람 기록 — 봇·식별 불가 요청은 기록하지 않고 False."""


class GenerateChatTrendRankingUseCase(ABC):
    @abstractmethod
    async def execute(self, days: int, limit: int) -> int:
        """chat_trend 랭킹을 집계·스냅샷 저장하고 저장 건수를 반환한다."""
