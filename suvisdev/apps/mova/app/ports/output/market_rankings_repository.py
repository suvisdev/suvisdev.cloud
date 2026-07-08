"""랭킹 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from mova.app.dtos.market_rankings_dto import (
    ChatTrendAggRowDto,
    ChatTrendRankingRowDto,
    RankingListDto,
)


class RankingsRepositoryPort(ABC):
    @abstractmethod
    async def get_hot(self, source: str, limit: int) -> RankingListDto:
        """HOT 랭킹 조회 (rankings → movies LEFT JOIN chat)."""

    @abstractmethod
    async def aggregate_chat_trend(self, days: int, limit: int) -> list[ChatTrendAggRowDto]:
        """최근 days일 picks를 movie_id별로 집계 — pick 횟수 + chat.hit_count 합산 상위 limit."""

    @abstractmethod
    async def save_chat_trend_ranking(
        self,
        rows: list[ChatTrendRankingRowDto],
        ranked_at: date,
    ) -> int:
        """source=chat_trend 스냅샷 저장 (동일 ranked_at 기존 행 덮어쓰기). 저장 건수 반환."""

    @abstractmethod
    async def save_box_office_ranking(self, movie_ids: list[int], ranked_at: date) -> int:
        """평점 상위 movie_ids 순서대로 box_office 스냅샷 저장."""
