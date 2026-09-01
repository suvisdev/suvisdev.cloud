"""검색 PgRepository — tags.label + movies.title ILIKE 검색."""

from __future__ import annotations

import logging

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.adapter.outbound.orm.studio_tags_orm import MovaTag
from mova.adapter.outbound.pg.weighted_rating import weighted_rating_expr
from mova.app.dtos.studio_movies_dto import MovieListItemDto
from mova.app.dtos.studio_search_dto import SearchResultDto
from mova.app.ports.output.studio_search_repository import SearchRepositoryPort

logger = logging.getLogger(__name__)


class SearchPgRepository(SearchRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_by_label(self, q: str, limit: int, offset: int) -> SearchResultDto:
        like_q = f"%{q}%"
        prefix_q = f"{q}%"

        where_clauses = [
            MovaTag.label.ilike(like_q),
            MovaMovie.title.ilike(like_q),
        ]

        # 배우·감독 확장은 2글자 이상일 때만 — 한 글자 검색(예: "아")은
        # 이름 어딘가에 한 글자가 들어간 배우/감독이 압도적으로 많아, 확장하면
        # title 매칭이 노이즈에 묻힌다(2026-08-13 실측: "아" → 관련 없는 영화 상단).
        if len(q.strip()) >= 2:
            actor_movie_ids = (
                select(MovaCharacter.movie_id)
                .join(MovaActor, MovaActor.id == MovaCharacter.actor_id)
                .where(MovaActor.name.ilike(like_q))
            )
            director_movie_ids = (
                select(MovaMovieDirector.movie_id)
                .join(MovaActor, MovaActor.id == MovaMovieDirector.actor_id)
                .where(MovaActor.name.ilike(like_q))
            )
            where_clauses.append(MovaMovie.id.in_(actor_movie_ids))
            where_clauses.append(MovaMovie.id.in_(director_movie_ids))

        matching_ids = (
            select(MovaMovie.id)
            .join(MovaTag, MovaTag.movie_id == MovaMovie.id, isouter=True)
            .where(or_(*where_clauses))
            .distinct()
            .subquery()
        )

        total = (
            await self._session.execute(select(func.count()).select_from(matching_ids))
        ).scalar_one()

        # 관련성 우선 정렬: title 시작일치 → title 부분일치 → 그 외(태그/배우/감독).
        # 동점 그룹 내에서만 평점 내림차순으로 배열해 유명작이 상단에 오도록 한다.
        match_score = case(
            (MovaMovie.title.ilike(prefix_q), 0),
            (MovaMovie.title.ilike(like_q), 1),
            else_=2,
        )

        movies = (
            (
                await self._session.execute(
                    select(MovaMovie)
                    .where(MovaMovie.id.in_(select(matching_ids.c.id)))
                    .order_by(match_score, weighted_rating_expr().desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )

        items = [MovieListItemDto.from_orm(m) for m in movies]
        logger.debug("[SearchPgRepository] q=%r total=%d returned=%d", q, total, len(items))
        return SearchResultDto(query=q, items=items, total=total, limit=limit, offset=offset)
