"""유저 취향 벡터 재계산 유스케이스.

두 진입점 공유:
- **BackgroundTasks**: 리뷰 임베딩 저장 성공 후 이어서(같은 BG task에서 체이닝) —
  본인 취향 벡터가 즉시 최신화된다.
- **CLI 크론**: 매일 KST 03:45. BG task가 실패했거나 유실된 유저를 잡는
  안전망. 리뷰 임베딩 백필(03:00)·리뷰 임베딩 CLI(03:30) 뒤 15분 시차.

계산: `sum(rating_i * embedding_i) / sum(rating_i)` — 별점 가중 평균.
정규화는 안 한다 — 조회 경로가 cosine 거리 기반이라 스케일 불변이고,
필요 시 조회 쪽에서 후처리하는 게 저장값을 흐리지 않는다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from mova.app.dtos.platform_user_taste_vector_dto import UserTasteVectorDto

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], "AsyncSession"]


class UserTasteVectorRecomputeInteractor:
    def __init__(self, *, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def recompute_for_user(self, user_id: int) -> str:
        """유저 하나 재계산. 반환값: 'updated' | 'cleared'.

        - updated: 리뷰가 1건 이상 있어 벡터 갱신
        - cleared: 리뷰 0건(또는 유효 rating 합계 0) → vector=NULL로 명시 저장
        """
        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository
        from mova.adapter.outbound.pg.platform_user_taste_vectors_pg_repository import (
            UserTasteVectorsPgRepository,
        )

        async with self._session_factory() as session:
            reviews_repo = ReviewsPgRepository(session=session)
            reviews = await reviews_repo.list_embedded_reviews_by_user(user_id)
            taste_repo = UserTasteVectorsPgRepository(session=session)

            weights_sum = sum(rating for _, rating, _ in reviews)
            if not reviews or weights_sum <= 0:
                await taste_repo.upsert(user_id, None, 0)
                return "cleared"

            dim = len(reviews[0][2])
            weighted = [0.0] * dim
            for _, rating, embedding in reviews:
                for i, x in enumerate(embedding):
                    weighted[i] += rating * x
            avg = [x / weights_sum for x in weighted]

            await taste_repo.upsert(user_id, avg, len(reviews))
            return "updated"

    async def get_for_user(self, user_id: int) -> UserTasteVectorDto | None:
        """유저 취향 벡터 조회 — 행이 없으면(리뷰를 한 번도 안 남긴 유저) None."""
        from mova.adapter.outbound.pg.platform_user_taste_vectors_pg_repository import (
            UserTasteVectorsPgRepository,
        )

        async with self._session_factory() as session:
            repo = UserTasteVectorsPgRepository(session=session)
            return await repo.get_by_user_id(user_id)

    async def recompute_missing(self, limit: int | None) -> dict[str, int]:
        """embedding+rating 있는 유저 전원 재계산 — CLI 백필용."""
        from mova.adapter.outbound.pg.platform_user_taste_vectors_pg_repository import (
            UserTasteVectorsPgRepository,
        )

        async with self._session_factory() as session:
            repo = UserTasteVectorsPgRepository(session=session)
            user_ids = await repo.list_user_ids_with_rated_reviews(limit=limit)

        stats = {"updated": 0, "cleared": 0}
        for uid in user_ids:
            outcome = await self.recompute_for_user(uid)
            stats[outcome] = stats.get(outcome, 0) + 1
        return stats
