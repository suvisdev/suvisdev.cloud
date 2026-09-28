"""채팅 PgRepository — ChatRepositoryPort 구현체."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRecommendationSchema
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.adapter.outbound.orm.market_user_actions_orm import (
    ACTION_WATCHED,
    EVENT_ACTION_TYPES,
    MovaUserAction,
)
from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector
from mova.adapter.outbound.orm.studio_movies_orm import ALLOWED_ORIGINAL_LANGUAGES, MovaMovie
from mova.adapter.outbound.orm.studio_tags_orm import MovaTag
from mova.adapter.outbound.pg.weighted_rating import weighted_rating_expr
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.domain.value_objects.mood_expansion import POPULAR_GENRES
from mova.domain.value_objects.movie_title import MovieTitle, loose_title_key

logger = logging.getLogger(__name__)

# (id, title) 전체 목록 TTL 캐시 — 리포지토리 인스턴스는 요청마다 새로
# 만들어지므로 모듈 레벨에 둔다. 상세는 `_all_movie_titles` docstring.
_TITLES_CACHE_TTL_SECONDS = 600
_titles_cache: tuple[float, list[tuple[int, str]]] | None = None


_SUMMARY_CHARS = 60  # 프롬프트 토큰과 판단 근거의 절충 — 한 줄이면 충분하다


def _to_search_items(
    rows: list[MovaMovie],
    match_type: str,
    genres: dict[int, list[str]] | None = None,
) -> list[MovaSearchItemSchema]:
    """카탈로그 아이템. 장르·줄거리 요약을 함께 실어 LLM이 제목으로 추측하지 않게 한다.

    2026-09-22: 프롬프트가 제목·연도만 주던 탓에 "형사물 추천"에 무관한 작품을 고르고
    줄거리를 지어내는 실패가 v3 평가 패배 25건 중 최다 사유였다(카탈로그 16회).
    """
    gmap = genres or {}
    return [
        MovaSearchItemSchema(
            id=str(m.id),
            title=m.title,
            year=str(m.release_year or ""),
            rating=float(m.rating or 0),
            poster=m.poster_url or "",
            match_type=match_type,
            genres=", ".join(gmap.get(m.id, [])),
            summary=_shorten(m.synopsis),
            vote_count=int(m.vote_count or 0),
        )
        for m in rows
    ]


def _shorten(text: str | None) -> str:
    """줄거리 앞 한 문장(최대 _SUMMARY_CHARS자). 문장 경계를 우선한다."""
    if not text:
        return ""
    cleaned = " ".join(text.split())
    if len(cleaned) <= _SUMMARY_CHARS:
        return cleaned
    head = cleaned[:_SUMMARY_CHARS]
    cut = max(head.rfind("."), head.rfind("다 "), head.rfind(", "))
    return (head[: cut + 1] if cut > _SUMMARY_CHARS // 2 else head).strip() + "…"


class ChatPgRepository(ChatRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _movie_ids_by_tags(self, keywords: list[str]) -> tuple[set[int], set[int]]:
        """키워드별 태그 매칭 → (합집합, 전 키워드 교집합).

        교집합은 매칭 0건 키워드("영화" 같은 비태그 어휘)를 빼고, 실제 태그에
        걸린 키워드가 2개 이상일 때만 계산한다(아니면 빈 set) — "SF 드라마"처럼
        장르를 여러 개 함께 말한 질의에서 둘 다 가진 영화를 우선하기 위한
        신호다(2026-09-02 다중 장르 AND 결함 수정).
        """
        if not keywords:
            return set(), set()
        terms = keywords[:6]
        cond = or_(*[MovaTag.label.ilike(f"%{kw}%") for kw in terms])
        rows = await self._session.execute(
            select(MovaTag.movie_id, MovaTag.label).where(cond).distinct()
        )
        union: set[int] = set()
        per_kw: dict[str, set[int]] = {kw: set() for kw in terms}
        for movie_id, label in rows:
            union.add(movie_id)
            low = (label or "").lower()
            for kw in terms:
                if kw.lower() in low:
                    per_kw[kw].add(movie_id)
        matched = [ids for ids in per_kw.values() if ids]
        inter = set.intersection(*matched) if len(matched) >= 2 else set()
        return union, inter

    async def _movie_ids_by_titles(self, title_terms: list[str]) -> set[int]:
        """프랜차이즈 확장 제목(어벤져스, 스파이더맨 등) → 제목 부분일치 영화.

        공백 제거 매칭 포함 — "더문" ↔ "더 문" 등 띄어쓰기 차이를 허용한다.
        """
        if not title_terms:
            return set()
        terms = title_terms[:15]
        conds = []
        title_no_space = func.replace(MovaMovie.title, " ", "")
        for t in terms:
            conds.append(MovaMovie.title.ilike(f"%{t}%"))
            stripped = t.replace(" ", "")
            if stripped != t:
                conds.append(title_no_space.ilike(f"%{stripped}%"))
            else:
                conds.append(title_no_space.ilike(f"%{stripped}%"))
        rows = await self._session.execute(select(MovaMovie.id).where(or_(*conds)).distinct())
        return {r[0] for r in rows}

    async def _genres_for(self, rows: list[MovaMovie]) -> dict[int, list[str]]:
        return await self._genres_by_movie_ids([m.id for m in rows])

    async def _genres_by_movie_ids(self, movie_ids: list[int]) -> dict[int, list[str]]:
        """카탈로그에 실을 장르 라벨. 대중 장르 화이트리스트만 통과시킨다 —
        태그에는 키워드 백필로 들어온 잡다한 라벨이 섞여 있어 그대로 쓰면 프롬프트가
        길어지기만 한다(2026-09-22)."""
        if not movie_ids:
            return {}
        rows = await self._session.execute(
            select(MovaTag.movie_id, MovaTag.label).where(
                MovaTag.movie_id.in_(movie_ids), MovaTag.label.in_(POPULAR_GENRES)
            )
        )
        out: dict[int, list[str]] = {}
        for movie_id, label in rows:
            bucket = out.setdefault(int(movie_id), [])
            if label not in bucket and len(bucket) < 3:  # 3개면 성격이 드러난다
                bucket.append(str(label))
        return out

    async def _actor_names_in_text(self, keywords: list[str]) -> list[str]:
        """keywords 안에 DB 배우 실명이 들어 있으면 그 이름을 돌려준다.

        의도 추출의 `_guess_actors`는 "{이름} 배우|출연|이랑" 패턴만 잡아
        "톰 크루즈 영화 추천"처럼 뒤따르는 말이 없는 발화에서 배우를 놓치고,
        잡아도 공백 앞 한 토큰만 캡처해 "크루즈"로 줄어 동성 배우(테리·레이먼드
        크루즈)까지 물어온다(2026-09-22 실측). 배우를 놓치면 태그도 0건이라
        RAG의 제목 유사 히트("정글 크루즈")만 후보에 남는 게 무관 픽의 경로였다.

        keywords에는 원문 전체가 한 항목으로 들어오므로 그걸 건초더미로 쓴다.
        2자 이름은 일반 어휘와 겹치므로("공유"·"고수"·"권율") 3자 이상만 본다.
        """
        if not keywords:
            return []
        hay = " ".join(keywords)
        rows = await self._session.execute(
            select(MovaActor.name)
            .where(
                func.length(MovaActor.name) >= 3,
                MovaActor.name.op("~")("[가-힣]"),
                literal(hay).ilike(func.concat("%", MovaActor.name, "%")),
            )
            .order_by(func.length(MovaActor.name).desc())
            .limit(5)
        )
        return [r[0] for r in rows]

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

    def _language_cond(self) -> Any:
        return or_(
            MovaMovie.original_language.is_(None),
            MovaMovie.original_language.in_(ALLOWED_ORIGINAL_LANGUAGES),
        )

    def _hard_conds(
        self, countries: list[str] | None, year_min: int | None, year_max: int | None
    ) -> list[Any]:
        """국가·연도 하드 조건 — 태그 매칭 결과와 인기작 폴백 양쪽에 똑같이 건다."""
        # 언어 허용목록(ko·en)은 "맥락 없는 외국어 영화 노출 방지"가 목적이라,
        # 사용자가 국가를 명시한 요청("일본 애니메이션")에는 적용하지 않는다 —
        # 적용하면 ja 원어 작품이 전부 걸러져 recs=0 (2026-08-26 프로덕션 실측).
        conds = [] if countries else [self._language_cond()]
        if countries:
            # origin_country는 JSONB 배열(공동제작이면 ["US","GB"]) — 하나라도
            # 겹치면 통과. 아직 백필 안 된 로우(NULL)는 국가를 증명할 수 없어 제외한다.
            conds.append(or_(*[MovaMovie.origin_country.contains([c]) for c in countries]))
        if year_min is not None:
            conds.append(MovaMovie.release_year >= year_min)
        if year_max is not None:
            conds.append(MovaMovie.release_year <= year_max)
        return conds

    @staticmethod
    def _recency_first_order() -> list[Any]:
        """최근 15년 작품 우선, 그 안에서 평점순 — 콜드 스타트(취향 데이터 없음)
        추천에 1950~70년대 작품이 뜬금없이 뜨는 것 방지(2026-08-25 사용자 지적).
        연도 필터를 명시한 질의는 conds가 이미 좁혀서 이 정렬의 영향이 없다."""
        cutoff = datetime.now(UTC).year - 15
        # rating 단독 desc는 소수평가 5.0 노이즈가 후보를 오염 — 가중 평점 사용.
        return [(MovaMovie.release_year >= cutoff).desc(), weighted_rating_expr().desc()]

    async def _movies_by_ids(
        self, movie_ids: set[int], limit: int, conds: list[Any]
    ) -> list[MovaMovie]:
        rows = await self._session.execute(
            select(MovaMovie)
            .where(MovaMovie.id.in_(movie_ids), *conds)
            .order_by(*self._recency_first_order())
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
        title_terms: list[str] | None = None,
    ) -> list[MovaSearchItemSchema]:
        has_hard_filter = bool(countries) or year_min is not None or year_max is not None
        if not keywords and not actor_names and not title_terms and not has_hard_filter:
            return []

        conds = self._hard_conds(countries, year_min, year_max)

        # 프랜차이즈 제목 매칭이 있으면 최우선 — "마블"이 장르(액션) 근사보다
        # 실제 어벤져스/스파이더맨을 물어오는 것이 정확하다.
        title_ids = await self._movie_ids_by_titles(title_terms or [])
        if title_ids:
            rows = await self._movies_by_ids(title_ids, limit, conds)
            if rows:
                return _to_search_items(rows, "title", await self._genres_for(rows))

        tag_ids, tag_and_ids = await self._movie_ids_by_tags(keywords)
        # DB에 실재하는 배우 이름이 발화에 있으면 그것을 쓴다 — 정규식 추측보다
        # 정확하고, 성만 잡힌 이름("크루즈")으로 동성 배우가 섞이는 것도 막는다.
        db_actor_names = await self._actor_names_in_text(keywords)
        actor_ids = await self._movie_ids_by_actors(db_actor_names or actor_names or [])

        if tag_ids and actor_ids:
            both = tag_ids & actor_ids
            if both:
                ids, match_type = both, "actor+keyword"
            elif db_actor_names:
                # DB 실명이 잡힌 배우 질의는 배우 조건을 유지한다. "송강호 나오는 영화"의
                # keywords에는 "영화"가 남아(`['송강호','나오는','영화',...]`) tags.label
                # ILIKE '%영화%'로 태그가 대량 매칭되는데, 교집합이 비었다고 합집합으로
                # 완화하면 송강호와 무관한 영화가 후보를 채우고 LLM이 0편을 낸다
                # (2026-09-22 실측: 6/6 recs=0, 로그상 match_type=keyword).
                ids, match_type = actor_ids, "actor"
            else:
                ids, match_type = tag_ids | actor_ids, "keyword"
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
            # 다중 장르 AND 우선(2026-09-02): "SF 드라마"의 교집합 영화를 먼저
            # 조회해 앞에 두고 남는 자리만 합집합으로 보충한다 — 합집합 단독으로
            # 평점순 limit을 자르면 두 태그를 다 가진 영화가 통째로 밀릴 수 있다.
            # mood 확장(동의어 OR)은 보충 경로가 살아 있어 그대로 동작한다.
            prio = (tag_and_ids & ids) if match_type == "keyword" else set()
            if prio and prio != ids:
                rows = await self._movies_by_ids(prio, limit, conds)
                if len(rows) < limit:
                    rows += await self._movies_by_ids(ids - prio, limit - len(rows), conds)
            else:
                rows = await self._movies_by_ids(ids, limit, conds)
            if rows:
                return _to_search_items(rows, match_type, await self._genres_for(rows))

        # 아무 조건도 안 맞으면 완전히 빈 후보 대신 인기작으로 폴백한다 —
        # 빈 후보를 주면 LLM이 카탈로그에 없는 movie_id를 스스로 지어내고
        # enrich 단계에서 전부 드롭돼 "reply는 자신있는데 카드 0개"가 된다
        # (2026-08-06 실사용 재현: "주말에 몰아볼 시리즈 느낌 영화").
        fallback_rows = await self._session.execute(
            select(MovaMovie).where(*conds).order_by(*self._recency_first_order()).limit(limit)
        )
        fb = list(fallback_rows.scalars().all())
        return _to_search_items(fb, "popular_fallback", await self._genres_for(fb))

    async def get_catalog_items(self, movie_ids: list[int]) -> list[MovaSearchItemSchema]:
        if not movie_ids:
            return []
        rows = await self._session.execute(select(MovaMovie).where(MovaMovie.id.in_(movie_ids)))
        by_id = {m.id: m for m in rows.scalars().all()}
        ordered = [by_id[i] for i in movie_ids if i in by_id]
        return _to_search_items(ordered, "semantic", await self._genres_for(ordered))

    async def filter_movie_ids_by_year(
        self,
        movie_ids: list[int],
        year_min: int | None,
        year_max: int | None,
    ) -> set[int]:
        if not movie_ids:
            return set()
        # release_year=0(미상)은 판정 불가 — 연도 조건이 있으면 탈락시킨다.
        conds = [MovaMovie.id.in_(movie_ids), MovaMovie.release_year != 0]
        if year_min is not None:
            conds.append(MovaMovie.release_year >= year_min)
        if year_max is not None:
            conds.append(MovaMovie.release_year <= year_max)
        rows = await self._session.execute(select(MovaMovie.id).where(*conds))
        return {int(r) for r in rows.scalars().all()}

    async def search_movies_by_title(
        self, terms: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        ids = await self._movie_ids_by_titles(terms)
        if not ids:
            return []
        rows = await self._movies_by_ids(ids, limit, [])
        return _to_search_items(rows, "title")

    async def _all_movie_titles(self) -> list[tuple[int, str]]:
        """전체 (id, title) 목록 — 10분 TTL 모듈 캐시.

        제목 역조회·퍼지 검색이 매 호출 movies 전 행을 끌어오던 것을 줄인다
        (2026-09-11 리뷰). 카탈로그는 일 단위(스케줄러·수동 임포트)로만 변해
        10분 지연은 무해하다.
        """
        global _titles_cache  # noqa: PLW0603
        now = time.monotonic()
        if _titles_cache is not None and now - _titles_cache[0] < _TITLES_CACHE_TTL_SECONDS:
            return _titles_cache[1]
        rows = await self._session.execute(select(MovaMovie.id, MovaMovie.title))
        titles = [(mid, title) for mid, title in rows if title]
        _titles_cache = (now, titles)
        return titles

    async def find_movie_titled_in_text(self, text: str) -> MovaSearchItemSchema | None:
        """text 안에 제목이 그대로 들어간 영화를 역방향으로 찾는다(가장 긴 제목 우선).

        직전 assistant 문장에서 작품을 복원하는 용도라, 공백·대소문자를 무시하고
        정규화한 뒤 부분일치를 본다. 2자 이하 제목은 오탐이 커 제외한다.
        """
        if not loose_title_key(text):
            return None
        best: tuple[int, str] | None = None
        for mid, title in await self._all_movie_titles():
            candidate = MovieTitle(title or "")
            if not candidate.appears_in(text):
                continue
            if best is None or len(candidate.loose_key) > len(loose_title_key(best[1])):
                best = (mid, title)
        if best is None:
            return None
        found = await self._movies_by_ids({best[0]}, 1, [])
        return _to_search_items(found, "title")[0] if found else None

    async def fuzzy_search_movies_by_title(
        self, terms: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        """자모 편집거리 기반 퍼지 검색 — 캐시된 전체 제목을 Python에서 비교."""
        from mova.domain.value_objects.jamo_fuzzy import fuzzy_match_titles

        all_titles = await self._all_movie_titles()

        candidates: list[tuple[int, str, int]] = []
        for term in terms[:4]:
            candidates.extend(fuzzy_match_titles(term, all_titles, max_distance=3))

        seen: set[int] = set()
        unique: list[tuple[int, str, int]] = []
        for mid, title, dist in sorted(candidates, key=lambda x: x[2]):
            if mid not in seen:
                seen.add(mid)
                unique.append((mid, title, dist))
            if len(unique) >= limit:
                break

        if not unique:
            return []
        ids = {mid for mid, _, _ in unique}
        rows2 = await self._movies_by_ids(ids, limit, [])
        items = _to_search_items(rows2, "fuzzy")
        id_dist = {mid: dist for mid, _, dist in unique}
        items.sort(key=lambda i: id_dist.get(int(i.id), 99))
        return items

    async def record_user_action(self, user_id: int, movie_id: int, action_type: str) -> None:
        if action_type not in EVENT_ACTION_TYPES:
            logger.warning("[ChatPgRepository] 미정의 action_type=%s — 기록 생략", action_type)
            return
        self._session.add(
            MovaUserAction(user_id=user_id, movie_id=movie_id, action_type=action_type)
        )
        await self._session.commit()

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

    async def get_watched_movie_ids(self, user_id: int) -> set[str]:
        rows = (
            await self._session.execute(
                select(MovaUserAction.movie_id)
                .where(
                    MovaUserAction.user_id == user_id,
                    MovaUserAction.action_type == ACTION_WATCHED,
                )
                .distinct()
            )
        ).all()
        return {str(r[0]) for r in rows if r[0] is not None}

    async def save_chat(
        self,
        *,
        user_id: int | None,
        assistant_id: int | None,
        raw_message: str,
        refined_query: str,
        keywords: list[str],
        intent_type: str,
        search_filters: dict[str, Any],
        reply: str | None,
    ) -> int:
        chat = MovaChat(
            user_id=user_id,
            assistant_id=assistant_id,
            raw_message=raw_message,
            refined_query=refined_query,
            keywords=keywords,
            intent_type=intent_type,
            search_filters=search_filters,
            reply=reply,
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
                    hook=(rec.hook or "")[:80] or None,
                    title_snapshot=rec.title,
                    batch_at=batch_at,
                    feedback=None,
                )
            )
        await self._session.commit()
        logger.debug("[ChatPgRepository] picks saved chat_id=%d count=%d", chat_id, len(slugs))
