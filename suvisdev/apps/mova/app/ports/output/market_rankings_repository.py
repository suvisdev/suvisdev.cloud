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
        """HOT 랭킹 조회 (rankings → movies LEFT JOIN chat).

        가장 최근 ranked_at 스냅샷 한 건만 반환한다 — save_*_ranking()이
        매일 새 ranked_at으로 스냅샷을 추가만 하고 이전 날짜 행을 지우지
        않아, 필터가 없으면 여러 날짜의 rank 1~N이 그대로 섞여 나온다.
        """

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
