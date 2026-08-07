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
from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector
from mova.adapter.outbound.orm.studio_movies_orm import ALLOWED_ORIGINAL_LANGUAGES, MovaMovie
from mova.adapter.outbound.orm.studio_tags_orm import MovaTag
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort

logger = logging.getLogger(__name__)


def _to_search_items(rows: list[MovaMovie], match_type: str) -> list[MovaSearchItemSchema]:
    return [
        MovaSearchItemSchema(
            id=str(m.id),
            title=m.title,
            year=str(m.release_year or ""),
            rating=float(m.rating or 0),
            poster=m.poster_url or "",
            match_type=match_type,
        )
        for m in rows
    ]


class ChatPgRepository(ChatRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _movie_ids_by_tags(self, keywords: list[str]) -> set[int]:
        if not keywords:
            return set()
        cond = or_(*[MovaTag.label.ilike(f"%{kw}%") for kw in keywords[:6]])
        rows = await self._session.execute(
            select(MovaTag.movie_id).where(cond).distinct()
        )
        return {r[0] for r in rows}

    async def _movie_ids_by_actors(self, actor_names: list[str]) -> set[int]:
        if not actor_names:
            return set()
        name_cond = or_(*[MovaActor.name.ilike(f"%{n}%") for n in actor_names[:5]])
        cast_rows = await self._session.execute(
            select(MovaCharacter.movie_id)
            .join(MovaActor, MovaActor.id == MovaCharacter.actor_id)
            .where(name_cond)
            .distinct()
        )
        director_rows = await self._session.execute(
            select(MovaMovieDirector.movie_id)
            .join(MovaActor, MovaActor.id == MovaMovieDirector.actor_id)
            .where(name_cond)
            .distinct()
        )
        return {r[0] for r in cast_rows} | {r[0] for r in director_rows}

    def _language_cond(self):
        return or_(
            MovaMovie.original_language.is_(None),
            MovaMovie.original_language.in_(ALLOWED_ORIGINAL_LANGUAGES),
        )

    def _hard_conds(
        self, countries: list[str] | None, year_min: int | None, year_max: int | None
    ) -> list:
        """국가·연도 하드 조건 — 태그 매칭 결과와 인기작 폴백 양쪽에 똑같이 건다."""
        conds = [self._language_cond()]
        if countries:
            # origin_country는 JSONB 배열(공동제작이면 ["US","GB"]) — 하나라도
            # 겹치면 통과. 아직 백필 안 된 로우(NULL)는 국가를 증명할 수 없어 제외한다.
            conds.append(
                or_(*[MovaMovie.origin_country.contains([c]) for c in countries])
            )
        if year_min is not None:
            conds.append(MovaMovie.release_year >= year_min)
        if year_max is not None:
            conds.append(MovaMovie.release_year <= year_max)
        return conds

    async def _movies_by_ids(
        self, movie_ids: set[int], limit: int, conds: list
    ) -> list[MovaMovie]:
        rows = await self._session.execute(
            select(MovaMovie)
            .where(MovaMovie.id.in_(movie_ids), *conds)
            .order_by(MovaMovie.rating.desc())
            .limit(limit)
        )
        return list(rows.scalars().all())

    async def search_tag_catalog(
        self,
        keywords: list[str],
        limit: int,
        *,
        actor_names: list[str] | None = None,
        countries: list[str] | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
    ) -> list[MovaSearchItemSchema]:
        has_hard_filter = bool(countries) or year_min is not None or year_max is not None
        if not keywords and not actor_names and not has_hard_filter:
            return []

        conds = self._hard_conds(countries, year_min, year_max)

        tag_ids = await self._movie_ids_by_tags(keywords)
        actor_ids = await self._movie_ids_by_actors(actor_names or [])

        if tag_ids and actor_ids:
            both = tag_ids & actor_ids
            ids, match_type = (both, "actor+keyword") if both else (tag_ids | actor_ids, "keyword")
        elif actor_ids:
            ids, match_type = actor_ids, "actor"
        elif tag_ids:
            ids, match_type = tag_ids, "keyword"
        else:
            ids, match_type = set(), "keyword"

        # 태그/배우로 좁힌 결과에 하드 조건을 걸었을 때 0건이면, 조건을 푸는 대신
        # 하드 조건만 만족하는 인기작으로 간다 — "2020년대 한국 액션"에서 액션
        # 태그가 헐리우드만 물어와도 한국 2020년대 인기작이 후보로 남는다.
        if ids:
            rows = await self._movies_by_ids(ids, limit, conds)
            if rows:
                return _to_search_items(rows, match_type)

        # 아무 조건도 안 맞으면 완전히 빈 후보 대신 인기작으로 폴백한다 —
        # 빈 후보를 주면 LLM이 카탈로그에 없는 movie_id를 스스로 지어내고
        # enrich 단계에서 전부 드롭돼 "reply는 자신있는데 카드 0개"가 된다
        # (2026-08-06 실사용 재현: "주말에 몰아볼 시리즈 느낌 영화").
        fallback_rows = await self._session.execute(
            select(MovaMovie).where(*conds).order_by(MovaMovie.rating.desc()).limit(limit)
        )
        return _to_search_items(list(fallback_rows.scalars().all()), "popular_fallback")

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
