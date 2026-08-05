import json
import logging
import re

from pydantic import BaseModel, ValidationError

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRecommendationSchema
from mova.adapter.outbound.http import TmdbAdapter
from mova.adapter.outbound.orm.studio_movies_orm import slugify_movie
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.app.dtos.studio_import_dto import MovieUpsertCommand
from mova.app.dtos.studio_movies_dto import MovieDetailDto

logger = logging.getLogger(__name__)


_HANJA_PATTERN = re.compile(r"[一-鿿㐀-䶿]+")


class _GeminiPickSchema(BaseModel):
    """Gemini 원문 JSON의 pick 1건 검증 — movie_id 필수.

    title 문자열을 사후에 DB와 매칭하던 방식이 동명이인 오귀속("괴물"→
    The Thing)과 포맷 미매칭("빽 투 더 퓨쳐 (1985)") 두 버그의 공통 원인이었다
    (_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md). 프롬프트가 제시한
    카탈로그의 movie_id를 그대로 돌려받아 파싱 단계에서 검증하고, 없거나
    정수로 안 읽히면 그 pick만 드롭한다(전체 응답을 실패시키지 않음)."""

    movie_id: int
    title: str
    hook: str = ""
    synopsis: str = ""
    poster: str | None = None
    platform: str | None = None


def _strip_hanja(text: str) -> str:
    """소형 다국어 모델(Qwen 등)이 한국어 생성 중 한자를 섞는 경우가 실측됨
    ("취향에 맞는作品", "서른四个季节" 등) — "한국어로만" 프롬프트 지시만으로는
    신뢰할 수 없어(반복 재현됨), 한자 유니코드 블록을 코드 레벨로 강제 제거한다."""
    cleaned = _HANJA_PATTERN.sub("", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


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
        intro = _strip_hanja(str(data.get("intro", "")).strip() if data else raw.strip()[:300])
        picks = data.get("picks") if data else None

        recommendations: list[MovaChatRecommendationSchema] = []

        if isinstance(picks, list):
            for item in picks:
                if len(recommendations) >= 3:
                    break
                if not isinstance(item, dict):
                    continue
                try:
                    pick = _GeminiPickSchema.model_validate(item)
                except ValidationError:
                    logger.warning(
                        "[ChatReplyService] movie_id 없는/유효하지 않은 pick 드롭 — "
                        "카탈로그 grounding 위반 | item=%r",
                        item,
                    )
                    continue

                title = _strip_hanja(pick.title.strip())
                if not title:
                    continue
                hook = _strip_hanja(pick.hook.strip())[:120]
                platform = pick.platform.strip() if pick.platform and pick.platform.strip() else None
                recommendations.append(
                    MovaChatRecommendationSchema(
                        id=slugify_movie(title),
                        movie_id=pick.movie_id,
                        title=title,
                        poster=_coerce_poster(pick.poster),
                        synopsis=pick.synopsis.strip()[:100] if pick.synopsis else "",
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
        """Gemini가 카탈로그에서 고른 movie_id로 직접 조회한다.

        2026-08-05 이전엔 title 문자열을 canonical map→slug→find_by_title
        순으로 사후 재매칭했다 — 이게 동명이인 오귀속·포맷 미매칭 두 버그의
        공통 원인이었다(_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md).
        이제 title 매칭을 하지 않으므로 두 버그 모두 이 경로에서 원천 차단된다.
        movie_id가 실제 DB에 없으면(Gemini가 카탈로그를 무시한 프롬프트 위반)
        그 pick만 드롭한다 — 예전처럼 미확인 제목으로 placeholder movie를
        새로 만들지 않는다(카탈로그 밖 데이터가 DB에 섞이는 것 방지).
        """
        if not recommendations:
            return []

        factory = get_mova_session_factory()
        enriched: list[MovaChatRecommendationSchema] = []

        async with factory() as session:
            repo = MoviesPgRepository(session)
            for rec in recommendations:
                movie = await repo.find_by_id(rec.movie_id) if rec.movie_id is not None else None
                if movie is None:
                    logger.warning(
                        "[ChatReplyService] 카탈로그에 없는 movie_id 응답 — 드롭 | "
                        "movie_id=%s title=%r",
                        rec.movie_id,
                        rec.title,
                    )
                    continue

                poster = _coerce_poster(rec.poster)
                year = rec.year
                platform = rec.platform
                if not poster:
                    poster = (movie.poster_url or "").strip()
                if not year:
                    year = str(movie.release_year or "")
                if not platform:
                    platform = _platform_from_dto(movie)

                if not poster:
                    poster = await self._fetch_tmdb_poster(rec.title, year)

                if poster and poster != (movie.poster_url or "").strip():
                    try:
                        await repo.upsert_movie(
                            MovieUpsertCommand(
                                slug=movie.slug,
                                title=movie.title,
                                release_year=movie.release_year or 0,
                                rating=movie.rating,
                                poster_url=poster,
                                # 빈 리스트 → upsert_movie가 genre 태그를 건드리지 않음(기존 유지).
                                genres=[],
                            )
                        )
                    except Exception:
                        logger.debug(
                            "[ChatReplyService] 포스터 갱신 스킵 — %r",
                            rec.title,
                            exc_info=True,
                        )

                enriched.append(
                    rec.model_copy(
                        update={
                            "id": movie.slug,
                            "movie_id": movie.id,
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
            pass

        # 소형 로컬 모델은 "JSON만 출력" 지시를 어기고 예시·부연설명을 뒤에 덧붙이는 경우가
        # 있다(EXAONE AWQ에서 실측). 첫 `{`부터 그리디하게 마지막 `}`까지 긁으면 여러 JSON
        # 블록이 한 덩어리로 잡혀 깨지므로, 첫 번째로 완결되는 JSON 객체 하나만 추출한다.
        start = text.find("{")
        if start != -1:
            try:
                data, _ = json.JSONDecoder().raw_decode(text, start)
                return data
            except json.JSONDecodeError:
                pass

        logger.warning("[ChatReplyService] JSON 파싱 실패")
        return None
