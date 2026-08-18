"""유저 취향 벡터 PgRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_reviews_orm import MovaReview
from mova.adapter.outbound.orm.platform_user_taste_vectors_orm import MovaUserTasteVector
from mova.app.dtos.platform_user_taste_vector_dto import UserTasteVectorDto
from mova.app.ports.output.platform_user_taste_vector_repository import (
    UserTasteVectorRepositoryPort,
)


class UserTasteVectorsPgRepository(UserTasteVectorRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, user_id: int, vector: list[float] | None, review_count: int
    ) -> None:
        # ON CONFLICT (user_id) — vector·review_count 갱신.
        # updated_at은 컬럼 default `now()`가 INSERT에만 걸리므로,
        # UPDATE 경로에서는 `now()`를 명시적으로 넣어 stale 방지.
        from sqlalchemy import text as sql_text

        stmt = (
            pg_insert(MovaUserTasteVector)
            .values(user_id=user_id, vector=vector, review_count=review_count)
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "vector": vector,
                    "review_count": review_count,
                    "updated_at": sql_text("now()"),
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_by_user_id(self, user_id: int) -> UserTasteVectorDto | None:
        row = (
            await self._session.execute(
                select(MovaUserTasteVector).where(MovaUserTasteVector.user_id == user_id)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return UserTasteVectorDto(
            user_id=row.user_id,
            vector=list(row.vector) if row.vector is not None else None,
            review_count=row.review_count,
            updated_at=row.updated_at,
        )

    async def get_taste_vector(self, user_id: int) -> list[float] | None:
        row = (
            await self._session.execute(
                select(MovaUserTasteVector.vector).where(
                    MovaUserTasteVector.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        return list(row) if row is not None else None

    async def list_user_ids_with_rated_reviews(self, limit: int | None) -> list[int]:
        stmt = (
            select(MovaReview.user_id)
            .where(MovaReview.embedding.is_not(None), MovaReview.rating.is_not(None))
            .group_by(MovaReview.user_id)
            .order_by(MovaReview.user_id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).all()
        return [uid for (uid,) in rows]
