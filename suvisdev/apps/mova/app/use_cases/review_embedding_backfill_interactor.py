"""리뷰 body → embedding 백필 유스케이스.

두 진입점에서 재사용된다.
- **Router BackgroundTasks**: `add_review`/`update_review` 성공 후 백그라운드에서
  개별 리뷰 하나 처리(embed_one).
- **CLI 크론**: 매일 EC2에서 `embedding IS NULL` 잔여를 순회(embed_missing) —
  BackgroundTasks가 실패했거나 재시작으로 유실된 건을 잡는 안전망.

두 경로 다 **요청 세션 밖에서 동작**한다(BackgroundTasks는 응답 반환 후 실행,
CLI는 세션이 아예 없음). 그래서 인터랙터가 세션 팩토리를 직접 받고 내부에서
`async with factory() as session:`로 세션을 새로 뽑는다 — 요청 세션에 붙지
않아야 리뷰 저장 트랜잭션과 임베딩 저장 트랜잭션이 서로를 막지 않는다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# BackgroundTasks 진입점에서는 factory가 async context manager를 만드는 콜러블이다.
SessionFactory = Callable[[], "AsyncSession"]


class ReviewEmbeddingBackfillInteractor:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        embedder: EmbeddingPort,
    ) -> None:
        self._session_factory = session_factory
        self._embedder = embedder

    async def embed_one(self, review_id: int) -> str:
        """리뷰 하나 처리. 반환값: 'succeeded' | 'skipped' | 'failed'.

        - skipped: body가 없거나 리뷰가 존재하지 않음(→ 정상, 재시도 불필요)
        - failed: Gemini 호출 실패(→ crontab 백필이 나중에 재시도)
        """
        # lazy import — mova/app 레이어에서 outbound adapter 직접 참조를 피한다.
        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        async with self._session_factory() as session:
            repo = ReviewsPgRepository(session=session)
            body = await repo.get_body_for_embedding(review_id)
            if body is None:
                return "skipped"
            try:
                vector = await self._embedder.embed(body)
            except HubRagError:
                logger.warning(
                    "[review_embedding_backfill] 임베딩 호출 실패 | review_id=%s",
                    review_id,
                    exc_info=True,
                )
                return "failed"
            await repo.update_embedding(review_id, vector)
            return "succeeded"

    async def embed_missing(self, limit: int | None) -> dict[str, int]:
        """embedding IS NULL 잔여 순회 — CLI 백필용. dict 카운트 반환."""
        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        stats = {"succeeded": 0, "failed": 0, "skipped": 0}
        async with self._session_factory() as session:
            repo = ReviewsPgRepository(session=session)
            targets = await repo.list_missing_embedding(limit=limit)

        for review_id, _body in targets:
            outcome = await self.embed_one(review_id)
            stats[outcome] += 1

        return stats
