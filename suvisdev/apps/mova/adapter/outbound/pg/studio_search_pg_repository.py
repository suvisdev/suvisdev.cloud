"""검색 PgRepository — tags.label + movies.title ILIKE 검색."""

from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.adapter.outbound.orm.studio_tags_orm import MovaTag
from mova.app.dtos.studio_movies_dto import MovieListItemDto
from mova.app.dtos.studio_search_dto import SearchResultDto
from mova.app.ports.output.studio_search_repository import SearchRepositoryPort

logger = logging.getLogger(__name__)


class SearchPgRepository(SearchRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_by_label(self, q: str, limit: int, offset: int) -> SearchResultDto:
        like_q = f"%{q}%"

        # 배우·감독 이름(actors.name)에 q가 포함되는 movie_id 서브쿼리 —
        # 각각 characters·movie_directors를 통해 join.
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

        # 태그 label, 영화 제목, 배우·감독 이름 중 하나라도 일치하는 movie.id 집합.
        matching_ids = (
            select(MovaMovie.id)
            .join(MovaTag, MovaTag.movie_id == MovaMovie.id, isouter=True)
            .where(
                or_(
                    MovaTag.label.ilike(like_q),
                    MovaMovie.title.ilike(like_q),
                    MovaMovie.id.in_(actor_movie_ids),
                    MovaMovie.id.in_(director_movie_ids),
                )
            )
            .distinct()
            .subquery()
        )

        total = (
            await self._session.execute(select(func.count()).select_from(matching_ids))
        ).scalar_one()

        movies = (
            (
                await self._session.execute(
                    select(MovaMovie)
                    .where(MovaMovie.id.in_(select(matching_ids.c.id)))
                    .order_by(MovaMovie.rating.desc())
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
