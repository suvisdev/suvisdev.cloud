"""리뷰 집계 출력 포트 — evaluate 트랙(작품 평가) 전용."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_chat_dto import ReviewAggregateDto


class ReviewAggregationPort(ABC):
    @abstractmethod
    async def aggregate_for_movie(
        self, movie_id: int, *, excerpt_limit: int = 3
    ) -> ReviewAggregateDto:
        """자체 리뷰 건수·평균 평점·대표 발췌를 집계한다.

        발췌는 스포일러 구간(spoiler_spans)이 있는 리뷰를 제외한 최신 본문에서
        고른다 — 평가 응답에 스포일러를 인용하지 않기 위해(마스킹 대신 제외,
        Phase 1 단순화).
        """
