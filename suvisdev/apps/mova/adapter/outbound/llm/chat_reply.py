import json
import logging
import re

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRecommendationSchema
from mova.adapter.outbound.http import TmdbAdapter
from mova.adapter.outbound.orm.studio_movies_orm import slugify_movie
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.app.dtos.studio_import_dto import MovieUpsertCommand
from mova.app.dtos.studio_movies_dto import MovieDetailDto
from mova.domain.value_objects.studio_movies_vo import resolve_canonical_slug

logger = logging.getLogger(__name__)


def _coerce_poster(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("url", "src", "href", "poster"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        return ""
    return str(value).strip() if value else ""


def _platform_from_dto(movie: MovieDetailDto) -> str | None:
    if not movie.platforms:
        return None
    provider = movie.platforms[0].provider
    return provider or None


class ChatReplyService:
    def parse_gemini_reply(self, raw: str) -> tuple[str, list[MovaChatRecommendationSchema]]:
        data = self._extract_json(raw)
        intro = str(data.get("intro", "")).strip() if data else raw.strip()[:300]
        picks = data.get("picks") if data else None

        recommendations: list[MovaChatRecommendationSchema] = []

        if isinstance(picks, list):
            for item in picks[:3]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip()
                if not title:
                    title = str(item.get("slug", "")).strip()
                if not title:
                    continue
                hook = str(item.get("hook", "")).strip()[:120]
                platform_raw = item.get("platform")
                platform = (
                    str(platform_raw).strip()
                    if isinstance(platform_raw, str) and platform_raw.strip()
                    else None
                )
                recommendations.append(
                    MovaChatRecommendationSchema(
                        id=slugify_movie(title),
                        title=title,
                        year=str(item.get("year", "")).strip() or "",
                        poster=_coerce_poster(item.get("poster")),
                        synopsis=str(item.get("synopsis", "")).strip()[:100] or "",
                        platform=platform,
                        hook=hook or "취향에 맞는 작품이에요.",
                    ),
                )

        if not intro and recommendations:
            intro = "요청하신 취향에 맞춰 아래 작품 3편을 골라봤어요."
        elif not intro:
            intro = "추천을 준비하지 못했어요. 다시 질문해 주세요."

        return intro, recommendations[:3]

    async def enrich_from_db(
        self,
        recommendations: list[MovaChatRecommendationSchema],
    ) -> list[MovaChatRecommendationSchema]:
        if not recommendations:
            return []

        factory = get_mova_session_factory()
        enriched: list[MovaChatRecommendationSchema] = []

        async with factory() as session:
            repo = MoviesPgRepository(session)
            for rec in recommendations:
                canonical = resolve_canonical_slug(rec.id, title=rec.title)
                movie = (
                    await repo.get_by_slug(canonical)
                    or await repo.get_by_slug(rec.id)
                    or await repo.find_by_title(rec.title)
                )
                poster = _coerce_poster(rec.poster)
                year = rec.year
                platform = rec.platform
                slug = canonical if canonical != "movie" else rec.id
                if movie is not None:
                    slug = movie.slug
                    if not poster:
                        poster = (movie.poster_url or "").strip()
                    if not year:
                        year = movie.release_year or ""
                    if not platform:
                        platform = _platform_from_dto(movie)

                if not poster:
                    poster = await self._fetch_tmdb_poster(rec.title, year)

                try:
                    if movie is not None:
                        if poster and poster != (movie.poster_url or "").strip():
                            await repo.upsert_movie(
                                MovieUpsertCommand(
                                    slug=movie.slug,
                                    title=movie.title,
                                    release_year=movie.release_year or "",
                                    rating=movie.rating,
                                    poster_url=poster,
                                    genres=list(movie.genres or []),
                                )
                            )
                    else:
                        await repo.upsert_movie(
                            MovieUpsertCommand(
                                slug=slug,
                                title=rec.title,
                                release_year=year or "",
                                rating=0.0,
                                poster_url=poster or "",
                                genres=[],
                            )
                        )
                except Exception:
                    logger.debug(
                        "[ChatReplyService] 영화 DB 저장 스킵 — %r",
                        rec.title,
                        exc_info=True,
                    )

                enriched.append(
                    rec.model_copy(
                        update={
                            "id": slug,
                            "movie_id": movie.id if movie is not None else None,
                            "poster": poster,
                            "year": year,
                            "platform": platform,
                        },
                    ),
                )
        return enriched

    async def _fetch_tmdb_poster(self, title: str, year: str) -> str:
        try:
            key = get_keymaker().tmdb_api_key
            if not key:
                return ""
            adapter = TmdbAdapter(key)
            results = await adapter.search_movies(title, page=1)
            if not results:
                return ""
            pick = results[0]
            for c in results:
                ct = str(c.get("title") or c.get("original_title") or "").strip()
                cy = c.get("release_date", "")[:4]
                if ct == title and (not year or cy == year):
                    pick = c
                    break
            return adapter.poster_url(pick.get("poster_path")) or ""
        except Exception:
            return ""

    def _extract_json(self, raw: str) -> dict | None:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        logger.warning("[ChatReplyService] JSON 파싱 실패")
        return None
