"""채팅 PgRepository — ChatRepositoryPort 구현체."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRecommendationSchema
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.adapter.outbound.orm.studio_tags_orm import MovaTag
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort

logger = logging.getLogger(__name__)


class ChatPgRepository(ChatRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_tag_catalog(
        self, keywords: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        if not keywords:
            return []

        cond = or_(*[MovaTag.label.ilike(f"%{kw}%") for kw in keywords[:6]])
        rows = (
            (
                await self._session.execute(
                    select(MovaMovie)
                    .join(MovaTag, MovaTag.movie_id == MovaMovie.id)
                    .where(cond)
                    .distinct()
                    .order_by(MovaMovie.rating.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .unique()
            .all()
        )

        return [
            MovaSearchItemSchema(
                id=str(m.id),
                title=m.title,
                year=m.release_year or "",
                rating=float(m.rating or 0),
                poster=m.poster_url or "",
                match_type="keyword",
            )
            for m in rows
        ]

    async def get_recent_intents_by_user(self, user_id: int, limit: int) -> list[MovaChat]:
        rows = (
            (
                await self._session.execute(
                    select(MovaChat)
                    .where(MovaChat.user_id == user_id)
                    .order_by(MovaChat.last_used_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def save_chat(
        self,
        *,
        user_id: int | None,
        assistant_id: int | None,
        raw_message: str,
        refined_query: str,
        keywords: list[str],
        intent_type: str,
        search_filters: dict,
    ) -> int:
        chat = MovaChat(
            user_id=user_id,
            assistant_id=assistant_id,
            raw_message=raw_message,
            refined_query=refined_query,
            keywords=keywords,
            intent_type=intent_type,
            search_filters=search_filters,
            hit_count=1,
        )
        self._session.add(chat)
        await self._session.flush()
        chat_id = chat.id
        await self._session.commit()
        logger.debug("[ChatPgRepository] saved chat_id=%d", chat_id)
        return chat_id

    async def save_picks(
        self,
        *,
        chat_id: int,
        user_id: int | None,
        recommendations: list[MovaChatRecommendationSchema],
        batch_at: datetime,
    ) -> None:
        slugs = [r.id for r in recommendations if r.id]
        if not slugs:
            return

        movie_rows = (
            await self._session.execute(
                select(MovaMovie.id, MovaMovie.slug).where(MovaMovie.slug.in_(slugs))
            )
        ).all()
        movies_by_slug = {row.slug: row.id for row in movie_rows}

        for rank, rec in enumerate(recommendations[:3], start=1):
            movie_id = movies_by_slug.get(rec.id)
            if movie_id is None:
                logger.debug("[ChatPgRepository] pick 스킵 — slug=%r 없음", rec.id)
                continue
            self._session.add(
                MovaPick(
                    chat_id=chat_id,
                    user_id=user_id,
                    movie_id=movie_id,
                    pick_rank=rank,
                    hook=(rec.hook or "")[:120] or None,
                    title_snapshot=rec.title,
                    batch_at=batch_at,
                    feedback=None,
                )
            )
        await self._session.commit()
        logger.debug("[ChatPgRepository] picks saved chat_id=%d count=%d", chat_id, len(slugs))
