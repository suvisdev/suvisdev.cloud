"""ReviewAggregationPort 구현 — reviews 테이블 집계(evaluate 트랙 전용)."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_reviews_orm import MovaReview
from mova.app.dtos.market_chat_dto import ReviewAggregateDto
from mova.app.ports.output.review_aggregation_port import ReviewAggregationPort

logger = logging.getLogger(__name__)

_EXCERPT_MAX_CHARS = 200
# 발췌 후보를 넉넉히 가져와 스포일러 리뷰를 걸러도 excerpt_limit을 채우게 한다.
_EXCERPT_FETCH_MULTIPLIER = 4


class ReviewAggregationPgRepository(ReviewAggregationPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def aggregate_for_movie(
        self, movie_id: int, *, excerpt_limit: int = 3
    ) -> ReviewAggregateDto:
        summary = (
            await self._session.execute(
                select(
                    func.count(MovaReview.id),
                    func.avg(MovaReview.rating),
                ).where(MovaReview.movie_id == movie_id)
            )
        ).one()
        review_count = int(summary[0] or 0)
        avg_rating = round(float(summary[1]), 2) if summary[1] is not None else None

        rows = (
            await self._session.execute(
                select(MovaReview.body, MovaReview.spoiler_spans)
                .where(MovaReview.movie_id == movie_id, MovaReview.body.is_not(None))
                .order_by(MovaReview.created_at.desc())
                .limit(excerpt_limit * _EXCERPT_FETCH_MULTIPLIER)
            )
        ).all()
        excerpts: list[str] = []
        for body, spans in rows:
            text = (body or "").strip()
            if not text:
                continue
            # 스포일러 구간이 있는 리뷰는 인용하지 않는다(마스킹 대신 제외).
            if isinstance(spans, list) and spans:
                continue
            excerpts.append(text[:_EXCERPT_MAX_CHARS])
            if len(excerpts) >= excerpt_limit:
                break

        logger.debug(
            "[ReviewAggregationPgRepository] movie_id=%d count=%d avg=%s excerpts=%d",
            movie_id,
            review_count,
            avg_rating,
            len(excerpts),
        )
        return ReviewAggregateDto(
            review_count=review_count,
            avg_rating=avg_rating,
            excerpts=excerpts,
        )
