"""영화 PgRepository — MoviesRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.adapter.outbound.orm.studio_tags_orm import TAG_KIND_GENRE, MovaTag, slugify_tag
from mova.app.dtos.studio_import_dto import MovieUpsertCommand
from mova.app.dtos.studio_movies_dto import (
    MovieDetailDto,
    MovieFilterQuery,
    MovieListDto,
    MovieListItemDto,
)
from mova.app.ports.output.movies_repository import MoviesRepositoryPort

logger = logging.getLogger(__name__)


async def _replace_genre_tags(session: AsyncSession, movie_id: int, genres: list[str]) -> None:
    """movie_id의 tag_kind='genre' 태그를 genres로 통째로 교체한다."""
    await session.execute(
        delete(MovaTag).where(MovaTag.movie_id == movie_id, MovaTag.tag_kind == TAG_KIND_GENRE)
    )
    for g in genres:
        session.add(
            MovaTag(
                movie_id=movie_id,
                tag_kind=TAG_KIND_GENRE,
                slug=slugify_tag(g),
                label=g,
            )
        )


class MoviesPgRepository(MoviesRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> MovieDetailDto | None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.slug == slug))
        movie = movie_q.scalar_one_or_none()
        if not movie:
            return None

        char_actor_q = await self._session.execute(
            select(MovaCharacter, MovaActor)
            .join(MovaActor, MovaCharacter.actor_id == MovaActor.id)
            .where(MovaCharacter.movie_id == movie.id)
            .order_by(MovaActor.role_type, MovaActor.name)
        )
        char_actors = char_actor_q.all()

        tags_q = await self._session.execute(
            select(MovaTag)
            .where(MovaTag.movie_id == movie.id)
            .order_by(MovaTag.tag_kind, MovaTag.label)
        )
        tags = list(tags_q.scalars().all())

        logger.debug(
            "[MoviesPgRepository] get_by_slug=%s actors=%d tags=%d",
            slug,
            len(char_actors),
            len(tags),
        )
        genres = [t.label for t in tags if t.tag_kind == TAG_KIND_GENRE]
        return MovieDetailDto.from_orm(movie, char_actors, tags, genres)

    async def find_by_title(self, title: str) -> MovieDetailDto | None:
        movie_q = await self._session.execute(
            select(MovaMovie).where(MovaMovie.title == title).limit(1)
        )
        movie = movie_q.scalar_one_or_none()
        if not movie:
            return None
        return await self.get_by_slug(movie.slug)

    async def find_by_id(self, movie_id: int) -> MovieDetailDto | None:
        movie_q = await self._session.execute(
            select(MovaMovie).where(MovaMovie.id == movie_id).limit(1)
        )
        movie = movie_q.scalar_one_or_none()
        if not movie:
            return None
        return await self.get_by_slug(movie.slug)

    async def list_movies(self, query: MovieFilterQuery) -> MovieListDto:
        stmt = select(MovaMovie)
        count_stmt = select(func.count(MovaMovie.id))

        if query.genre:
            cond = (
                select(MovaTag.id)
                .where(
                    MovaTag.movie_id == MovaMovie.id,
                    MovaTag.tag_kind == TAG_KIND_GENRE,
                    MovaTag.label == query.genre,
                )
                .exists()
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.release_year:
            cond = MovaMovie.release_year == query.release_year
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.min_rating is not None:
            cond = MovaMovie.rating >= query.min_rating
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.age_rating:
            cond = MovaMovie.age_rating == query.age_rating
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.platform:
            cond = MovaMovie.platforms.contains([{"provider": query.platform}])
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.sort == "rating":
            stmt = stmt.order_by(MovaMovie.rating.desc())
        elif query.sort == "popular":
            stmt = stmt.order_by(MovaMovie.rating.desc())
        else:
            stmt = stmt.order_by(MovaMovie.release_year.desc(), MovaMovie.id.desc())

        total_r = await self._session.execute(count_stmt)
        total = total_r.scalar_one()

        stmt = stmt.limit(query.limit).offset(query.offset)
        movies_r = await self._session.execute(stmt)
        movies = list(movies_r.scalars().all())

        genres_by_movie: dict[int, list[str]] = {}
        if movies:
            movie_ids = [m.id for m in movies]
            genre_tags_r = await self._session.execute(
                select(MovaTag.movie_id, MovaTag.label).where(
                    MovaTag.movie_id.in_(movie_ids), MovaTag.tag_kind == TAG_KIND_GENRE
                )
            )
            for movie_id, label in genre_tags_r.all():
                genres_by_movie.setdefault(movie_id, []).append(label)

        logger.debug("[MoviesPgRepository] list_movies total=%d returned=%d", total, len(movies))
        return MovieListDto(
            items=[
                MovieListItemDto.from_orm(m, genres_by_movie.get(m.id, [])) for m in movies
            ],
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def count_movies(self) -> int:
        total_r = await self._session.execute(select(func.count(MovaMovie.id)))
        return int(total_r.scalar_one())

    async def list_all_slugs(self) -> list[tuple[int, str]]:
        rows = await self._session.execute(select(MovaMovie.id, MovaMovie.slug))
        return [(int(row.id), row.slug) for row in rows]

    async def upsert_movie(self, command: MovieUpsertCommand) -> int:
        existing_q = await self._session.execute(
            select(MovaMovie).where(MovaMovie.slug == command.slug)
        )
        existing = existing_q.scalar_one_or_none()
        if existing is None:
            movie = MovaMovie(
                slug=command.slug,
                title=command.title,
                release_year=command.release_year,
                rating=command.rating,
                poster_url=command.poster_url,
                platforms=list(command.platforms or []),
                age_rating=command.age_rating,
            )
            self._session.add(movie)
            await self._session.flush()
            if command.genres:
                await _replace_genre_tags(self._session, movie.id, list(command.genres))
            await self._session.commit()
            await self._session.refresh(movie)
            logger.debug("[MoviesPgRepository] insert slug=%s id=%d", command.slug, movie.id)
            return int(movie.id)

        existing.title = command.title
        existing.release_year = command.release_year
        existing.rating = command.rating
        if command.poster_url:
            existing.poster_url = command.poster_url
        if command.genres:
            await _replace_genre_tags(self._session, existing.id, list(command.genres))
        if command.age_rating is not None:
            existing.age_rating = command.age_rating
        await self._session.commit()
        await self._session.refresh(existing)
        logger.debug("[MoviesPgRepository] update slug=%s id=%d", command.slug, existing.id)
        return int(existing.id)
