"""리뷰 본문에서 스포일러 스팬을 감지·저장하는 백그라운드 인터랙터.

리뷰 POST/PATCH 응답 후 BackgroundTasks가 이 인터랙터의 detect_one을 호출한다.
Gemini 호출·DB 업데이트 모두 실패해도 조용히 스킵 — 리뷰 저장 자체는 이미
성공한 뒤라 사용자 UX에 영향 없음.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], "AsyncSession"]


class ReviewSpoilerBackfillInteractor:
    def __init__(self, *, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def detect_one(self, review_id: int) -> str:
        """리뷰 하나 처리. 반환: 'succeeded' | 'skipped' | 'failed'.

        - skipped: body가 없거나 리뷰가 존재하지 않음
        - failed: Gemini 호출 실패(쿼터·네트워크) — 그냥 스팬 비운 채 남김
        - succeeded: 감지 결과(빈 배열 포함)를 저장
        """
        from mova.adapter.outbound.llm.spoiler_detection import detect_spoiler_spans
        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        async with self._session_factory() as session:
            repo = ReviewsPgRepository(session=session)
            row = await repo.get_by_id(review_id)
            if row is None or not row.body or not row.body.strip():
                return "skipped"
            # 동기 SDK — 스레드 위임(이벤트 루프 블로킹 방지)
            try:
                spans = await asyncio.to_thread(detect_spoiler_spans, row.body)
            except Exception as e:
                logger.info("[spoiler_backfill] 감지 실패 review_id=%s err=%s", review_id, e)
                return "failed"
            await repo.update_spoiler_spans(review_id, spans)
            logger.info("[spoiler_backfill] review_id=%s spans=%d", review_id, len(spans))
            return "succeeded"
