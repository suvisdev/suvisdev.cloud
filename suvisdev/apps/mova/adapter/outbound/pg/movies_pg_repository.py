"""영화 PgRepository — MoviesRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector
from mova.adapter.outbound.orm.studio_movies_orm import ALLOWED_ORIGINAL_LANGUAGES, MovaMovie
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

        director_actor_q = await self._session.execute(
            select(MovaMovieDirector, MovaActor)
            .join(MovaActor, MovaMovieDirector.actor_id == MovaActor.id)
            .where(MovaMovieDirector.movie_id == movie.id)
            .order_by(MovaActor.name)
        )
        director_actors = director_actor_q.all()

        tags_q = await self._session.execute(
            select(MovaTag)
            .where(MovaTag.movie_id == movie.id)
            .order_by(MovaTag.tag_kind, MovaTag.label)
        )
        tags = list(tags_q.scalars().all())

        logger.debug(
            "[MoviesPgRepository] get_by_slug=%s actors=%d directors=%d tags=%d",
            slug,
            len(char_actors),
            len(director_actors),
            len(tags),
        )
        genres = [t.label for t in tags if t.tag_kind == TAG_KIND_GENRE]
        return MovieDetailDto.from_orm(movie, char_actors, tags, genres, director_actors)

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

        language_cond = or_(
            MovaMovie.original_language.is_(None),
            MovaMovie.original_language.in_(ALLOWED_ORIGINAL_LANGUAGES),
        )
        stmt = stmt.where(language_cond)
        count_stmt = count_stmt.where(language_cond)

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

        if query.actor:
            cond = (
                select(MovaCharacter.id)
                .join(MovaActor, MovaCharacter.actor_id == MovaActor.id)
                .where(
                    MovaCharacter.movie_id == MovaMovie.id,
                    MovaActor.name.ilike(f"%{query.actor}%"),
                )
                .exists()
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.release_year_min is not None:
            cond = MovaMovie.release_year >= query.release_year_min
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if query.release_year_max is not None:
            cond = MovaMovie.release_year <= query.release_year_max
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
            # "인기순" = AI 채팅에서 픽된 횟수(=사용자 검색·질의 결과로 노출된 횟수)
            # 내림차순, 동점이면 평점 내림차순. picks가 0건인 영화는 rating으로만 순위.
            # popularity 캐시 컬럼 대신 실시간 join — movies 규모(수천 편)에서 실용적.
            pick_count_sub = (
                select(MovaPick.movie_id, func.count().label("pick_count"))
                .group_by(MovaPick.movie_id)
                .subquery()
            )
            stmt = stmt.outerjoin(pick_count_sub, pick_count_sub.c.movie_id == MovaMovie.id)
            stmt = stmt.order_by(
                func.coalesce(pick_count_sub.c.pick_count, 0).desc(),
                MovaMovie.rating.desc(),
                MovaMovie.id.desc(),
            )
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

    async def list_missing_synopsis(self, limit: int | None) -> list[tuple[int, str]]:
        """synopsis가 비어 있는 TMDB 원산 영화 (movie.id, slug) — synopsis 백필 순회 전용."""
        stmt = (
            select(MovaMovie.id, MovaMovie.slug)
            .where(MovaMovie.synopsis.is_(None), MovaMovie.slug.like("tmdb-%"))
            .order_by(MovaMovie.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = await self._session.execute(stmt)
        return [(int(row.id), row.slug) for row in rows]

    async def update_synopsis(self, movie_id: int, synopsis: str) -> None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        movie = movie_q.scalar_one_or_none()
        if movie is None:
            return
        movie.synopsis = synopsis
        await self._session.commit()

    async def list_missing_original_language(self, limit: int | None) -> list[tuple[int, str]]:
        """original_language가 비어 있는 TMDB 원산 영화 (movie.id, slug) — 백필 순회 전용."""
        stmt = (
            select(MovaMovie.id, MovaMovie.slug)
            .where(MovaMovie.original_language.is_(None), MovaMovie.slug.like("tmdb-%"))
            .order_by(MovaMovie.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = await self._session.execute(stmt)
        return [(int(row.id), row.slug) for row in rows]

    async def update_original_language(self, movie_id: int, original_language: str) -> None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        movie = movie_q.scalar_one_or_none()
        if movie is None:
            return
        movie.original_language = original_language
        await self._session.commit()

    async def list_missing_origin_country(self, limit: int | None) -> list[tuple[int, str]]:
        """origin_country가 비어 있는 TMDB 원산 영화 (movie.id, slug) — 백필 순회 전용."""
        stmt = (
            select(MovaMovie.id, MovaMovie.slug)
            .where(MovaMovie.origin_country.is_(None), MovaMovie.slug.like("tmdb-%"))
            .order_by(MovaMovie.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = await self._session.execute(stmt)
        return [(int(row.id), row.slug) for row in rows]

    async def update_origin_country(self, movie_id: int, origin_country: list[str]) -> None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        movie = movie_q.scalar_one_or_none()
        if movie is None:
            return
        movie.origin_country = origin_country
        await self._session.commit()

    async def list_missing_age_rating_or_platforms(self, limit: int | None) -> list[tuple[int, str]]:
        """age_rating·platforms 둘 다 미백필(NULL/[])인 TMDB 원산 영화 (movie.id, slug).

        platforms는 NOT NULL default `[]`라 origin_country처럼 "NULL=미백필"로
        구분할 수 없다 — age_rating IS NULL AND platforms가 빈 배열, 둘 다일 때만
        미백필로 본다. TMDB에 실제로 등급·플랫폼 정보가 둘 다 없는 영화는 재실행마다
        다시 조회 대상에 걸리는 한계가 있다(일회성 수동 스크립트라 감내).
        """
        stmt = (
            select(MovaMovie.id, MovaMovie.slug)
            .where(
                MovaMovie.age_rating.is_(None),
                MovaMovie.platforms == [],
                MovaMovie.slug.like("tmdb-%"),
            )
            .order_by(MovaMovie.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = await self._session.execute(stmt)
        return [(int(row.id), row.slug) for row in rows]

    async def update_age_rating_and_platforms(
        self, movie_id: int, age_rating: str | None, platforms: list[dict[str, str | None]]
    ) -> None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        movie = movie_q.scalar_one_or_none()
        if movie is None:
            return
        movie.age_rating = age_rating
        movie.platforms = platforms
        await self._session.commit()

    async def list_missing_embedding(self, limit: int | None) -> list[tuple[int, str]]:
        """embedding이 NULL인 영화 (movie.id, slug) — 유사도 임베딩 백필 순회 전용.

        KOFIC 원산도 대상(origin_country 등과 달리 slug tmdb-* 제한 없음) —
        임베딩은 title/synopsis/genres/cast로 만들어 TMDB API 재조회가 필요
        없다(scripts/backfill_movie_embeddings_cli.py).
        """
        stmt = (
            select(MovaMovie.id, MovaMovie.slug)
            .where(MovaMovie.embedding.is_(None))
            .order_by(MovaMovie.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = await self._session.execute(stmt)
        return [(int(row.id), row.slug) for row in rows]

    async def update_embedding(self, movie_id: int, embedding: list[float]) -> None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        movie = movie_q.scalar_one_or_none()
        if movie is None:
            return
        movie.embedding = embedding
        await self._session.commit()

    async def find_similar_movies(self, slug: str, limit: int) -> list[MovieListItemDto] | None:
        movie_q = await self._session.execute(
            select(MovaMovie).where(MovaMovie.slug == slug)
        )
        movie = movie_q.scalar_one_or_none()
        if movie is None or movie.embedding is None:
            return None

        # pgvector HNSW planner cost 오판 회피: 2014행 규모에선 planner가
        # HNSW cost(~860) > Seq cost(~416)로 잘못 계산해 seq scan을 선택한다.
        # 실측으론 HNSW가 6.8배 빠름(10.2ms → 1.5ms, 2026-08-11). SET LOCAL은
        # 트랜잭션 종료 시 자동 원복이라 다른 세션엔 영향 없음.
        await self._session.execute(text("SET LOCAL enable_seqscan = off"))

        distance = MovaMovie.embedding.cosine_distance(movie.embedding)
        stmt = (
            select(MovaMovie)
            .where(MovaMovie.id != movie.id, MovaMovie.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()

        genres_by_movie: dict[int, list[str]] = {}
        if rows:
            movie_ids = [m.id for m in rows]
            genre_tags_r = await self._session.execute(
                select(MovaTag.movie_id, MovaTag.label).where(
                    MovaTag.movie_id.in_(movie_ids), MovaTag.tag_kind == TAG_KIND_GENRE
                )
            )
            for movie_id, label in genre_tags_r.all():
                genres_by_movie.setdefault(movie_id, []).append(label)

        return [MovieListItemDto.from_orm(m, genres_by_movie.get(m.id, [])) for m in rows]

    async def list_missing_trailer(self, limit: int | None) -> list[tuple[int, str]]:
        """trailer_key가 NULL인 TMDB 원산 영화 (movie.id, slug) — 백필 순회 전용."""
        stmt = (
            select(MovaMovie.id, MovaMovie.slug)
            .where(MovaMovie.trailer_key.is_(None), MovaMovie.slug.like("tmdb-%"))
            .order_by(MovaMovie.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = await self._session.execute(stmt)
        return [(int(row.id), row.slug) for row in rows]

    async def update_trailer_key(self, movie_id: int, trailer_key: str | None) -> None:
        movie_q = await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        movie = movie_q.scalar_one_or_none()
        if movie is None:
            return
        movie.trailer_key = trailer_key
        await self._session.commit()

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
                synopsis=command.synopsis,
                original_language=command.original_language or None,
                origin_country=command.origin_country,
                trailer_key=command.trailer_key,
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
        if command.platforms:
            existing.platforms = list(command.platforms)
        if command.synopsis:
            existing.synopsis = command.synopsis
        if command.original_language:
            existing.original_language = command.original_language
        if command.origin_country is not None:
            existing.origin_country = command.origin_country
        if command.trailer_key:
            existing.trailer_key = command.trailer_key
        await self._session.commit()
        await self._session.refresh(existing)
        logger.debug("[MoviesPgRepository] update slug=%s id=%d", command.slug, existing.id)
        return int(existing.id)
