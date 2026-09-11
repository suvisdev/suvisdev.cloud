"""리뷰 body → Echo 감정분석 백필 유스케이스.

GPU가 있는 로컬 머신에서만 동작한다(EXAONE-3.5-2.4B + LoRA 4bit).
EC2(GPU 없음)에서는 실행되지 않고 DB에 저장된 결과만 읽는다.

진입점:
- **CLI 배치**: `scripts/backfill_review_sentiment_cli.py`로 미처리 리뷰 순회.
- **Router BackgroundTasks**: 리뷰 POST/PATCH 후 GPU 있으면 개별 처리.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from ontology.adapter.outbound.resource_adapters.echo_sentiment.echo_sentiment_adapter import (
        EchoSentimentAdapter,
    )

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], "AsyncSession"]


def _make_echo_adapter() -> EchoSentimentAdapter:
    # ontology 어댑터는 lazy import — torch 로드가 무거워 GPU 경로에서만 당긴다.
    from pathlib import Path

    from ontology.adapter.outbound.resource_adapters.echo_sentiment.echo_sentiment_adapter import (
        EchoSentimentAdapter,
    )

    adapter_dir = (
        Path(__file__).resolve().parents[3] / "ontology" / "runs" / "echo_sentiment" / "adapter"
    )
    return EchoSentimentAdapter(adapter_dir=adapter_dir)


def sentiment_to_rating(label: str, score: float) -> float:
    """감정 라벨+신뢰도 → 0.5~5.0 별점 변환."""
    if label == "긍정":
        rating = 2.5 + score * 2.5
    else:
        rating = 2.5 - score * 2.0
    return max(0.5, min(5.0, round(rating * 2) / 2))


class ReviewSentimentBackfillInteractor:
    def __init__(self, *, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def analyze_one(self, review_id: int) -> str:
        """리뷰 하나 처리. 반환: 'succeeded' | 'skipped' | 'failed'.

        - skipped: body가 없거나 리뷰가 존재하지 않음
        - failed: Echo 모델 로드/추론 실패 (GPU 없음 포함)
        """
        import asyncio

        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        async with self._session_factory() as session:
            repo = ReviewsPgRepository(session=session)
            body = await repo.get_body_for_embedding(review_id)
            if body is None:
                return "skipped"
            try:
                adapter = _make_echo_adapter()
                result = await asyncio.to_thread(adapter.analyze, body)
            except Exception as e:
                logger.info("[sentiment_backfill] 분석 실패 review_id=%s err=%s", review_id, e)
                return "failed"
            await repo.update_sentiment(review_id, result.label, result.score)
            auto_rating = sentiment_to_rating(result.label, result.score)
            rated = await repo.update_rating_if_null(review_id, auto_rating)
            logger.info(
                "[sentiment_backfill] review_id=%s label=%s score=%.3f%s",
                review_id,
                result.label,
                result.score,
                f" auto_rating={auto_rating}" if rated else "",
            )
            return "succeeded"

    async def analyze_missing(self, limit: int | None) -> dict[str, int]:
        """sentiment_label IS NULL 잔여 순회 — CLI 배치용.

        모델을 한 번만 로드해 전량 추론(analyze_batch) 후 DB에 쓴다 —
        건당 로드/해제(analyze_one)로는 41건 ≈ 30분이던 것을 2~3분대로 줄인다
        (2026-09-02 백로그). Router BackgroundTasks의 단건 경로는 analyze_one
        그대로 유지.
        """
        import asyncio

        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        stats = {"succeeded": 0, "failed": 0, "skipped": 0}
        async with self._session_factory() as session:
            repo = ReviewsPgRepository(session=session)
            targets = await repo.list_missing_sentiment(limit=limit)
        if not targets:
            return stats

        try:
            adapter = _make_echo_adapter()
            results = await asyncio.to_thread(adapter.analyze_batch, [body for _, body in targets])
        except Exception as e:
            logger.info("[sentiment_backfill] 배치 분석 실패(모델 로드 등) err=%s", e)
            stats["failed"] = len(targets)
            return stats

        async with self._session_factory() as session:
            repo = ReviewsPgRepository(session=session)
            for (review_id, _body), result in zip(targets, results, strict=True):
                if result is None:
                    stats["failed"] += 1
                    continue
                await repo.update_sentiment(review_id, result.label, result.score)
                auto_rating = sentiment_to_rating(result.label, result.score)
                rated = await repo.update_rating_if_null(review_id, auto_rating)
                logger.info(
                    "[sentiment_backfill] review_id=%s label=%s score=%.3f%s",
                    review_id,
                    result.label,
                    result.score,
                    f" auto_rating={auto_rating}" if rated else "",
                )
                stats["succeeded"] += 1

        return stats
