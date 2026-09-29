"""MovaChatAgent — mova 채팅의 앱 두뇌 (2026-09-29, v9).

판단 모델(`mova-agent-v9`)이 발화·최근 대화·도구 결과를 읽고 다음 행동을 고르고, 허브 `AgentLoop`가
가드·예산 안에서 도구를 돌린다. 이 파일은 mova의 **도구 6개**와 **사실 템플릿**만 정의한다.

도구 두 종류(agent_loop 참고):
- 데이터 도구(여기서 실행): search_movie · get_movie_details · now_showing — 결과를 모델에 돌려주고,
  FINAL이면 `compose_facts`가 코드 템플릿으로 답을 쓴다(사실을 지어낼 여지 0 — 09-29 7.8B 실측).
- 터미널 도구(트랙이 실행): recommend_movies · showtimes · where_to_watch — `ChatInteractor`가 기존
  추천·예매 트랙으로 넘긴다(저장·응답을 트랙이 한 번에).

6칸 이해 단계(`ChatOrchestrator`)와의 차이·측정은 `apps/mova/_docs/MOVA_CHAT_ORCHESTRATOR.md` §8.
"""

from __future__ import annotations

import re
from typing import Any

from mova.adapter.outbound.llm.agent_prompt import MAX_STEPS, SYSTEM_PROMPT
from mova.app.ports.output.box_office_port import BoxOfficePort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.review_aggregation_port import ReviewAggregationPort
from mova.app.use_cases.market_chat_booking_interactor import BookingAssistService
from mova.app.use_cases.market_chat_title_resolver import resolve_movie_title
from mova.domain.value_objects.movie_title import MovieTitle
from ontology.app.agent.agent_loop import AgentDecision, AgentLoop, Tool
from ontology.app.ports.output.judge_port import JudgePort

_TERMINAL = {
    "recommend_movies": ("query",),
    "showtimes": ("title", "region", "date"),
    "where_to_watch": ("title",),
}
ASK_CAST = re.compile(r"누가|출연|배우|주연|감독|캐스팅|만들었")
ASK_PLOT = re.compile(r"줄거리|내용|무슨 ?영화|어떤 ?영화|스토리")


class MovaChatAgent:
    def __init__(
        self,
        *,
        judge: JudgePort,
        repository: ChatRepositoryPort,
        movies: MoviesRepositoryPort,
        reviews: ReviewAggregationPort,
        box_office: BoxOfficePort,
    ) -> None:
        self._repo = repository
        self._movies = movies
        self._reviews = reviews
        self._box_office = box_office
        # now_showing이 마지막으로 가져온 박스오피스 항목(개봉 연도 포함) — 모델에는 제목 목록만 주고(학습 형식 유지),
        # 인터랙터가 이걸로 상영작 카드를 만든다(동명작은 open_year가 맞는 쪽).
        self.last_box_office: list[Any] = []
        tools = [
            Tool("search_movie", ("title",), self.search_movie, grounded=("title",)),
            Tool("get_movie_details", ("title",), self.get_movie_details, grounded=("title",)),
            Tool("now_showing", (), self.now_showing),
            *[
                Tool(name, params, None, grounded=tuple(p for p in params if p != "query"))
                for name, params in _TERMINAL.items()
            ],
        ]
        self._loop = AgentLoop(
            judge=judge, system_prompt=SYSTEM_PROMPT, tools=tools, max_steps=MAX_STEPS
        )

    async def decide(
        self, message: str, history: list[dict[str, str]], *, trace_id: str
    ) -> AgentDecision:
        return await self._loop.run(message, history, trace_id=trace_id)

    # --- 데이터 도구 ------------------------------------------------------------------------

    async def _exact(self, title: str):
        """트랙과 같은 제목 해석기 — 조사·어절 후보·퍼지까지("데자뷰는 누가 나오지" → 데자뷰, 09-29 운영 실측:
        맥락 없이 오면 v9가 발화 전체를 title에 넣는다). 정확 일치면 item, 모호하면 후보 목록."""
        res = await resolve_movie_title(self._repo, message=title, entities=[title])
        items = await self._repo.search_movies_by_title([title], 8)
        if res.status == "ok" and res.item is not None:
            return res.item, items or [res.item]
        if res.status == "ambiguous" and res.candidates:
            return None, list(res.candidates)
        return None, items

    async def search_movie(self, title: str = "") -> dict[str, Any]:
        found, items = await self._exact(title)
        # 같은 이름으로 시작하는 작품을 최신순으로 — "타짜 요즘 개봉한 거"에 2026 신작이 보이게
        same = sorted(
            {f"{i.title} ({i.year})" for i in items}, key=lambda t: t[-5:-1], reverse=True
        )
        if found is not None:
            return {"found": f"{found.title} ({found.year})", "same_name_titles_newest_first": same}
        if items:
            return {"candidates": [f"{i.title} ({i.year})" for i in items[:5]]}
        return {"found": None, "note": f"카탈로그에 '{title}' 없음"}

    async def get_movie_details(self, title: str = "") -> dict[str, Any]:
        found, _ = await self._exact(title)
        if found is None:
            return await self.search_movie(title)
        d = await self._movies.find_by_id(int(found.id))
        if d is None:
            return {"found": None, "note": "작품 정보를 불러오지 못함"}
        agg = await self._reviews.aggregate_for_movie(int(found.id))
        return {
            "title": f"{d.title} ({d.release_year})",
            "director": [a.name for a in d.actors if a.character_id is None],
            "cast": [a.name for a in d.actors if a.character_id is not None][:6],
            "genres": d.genres,
            "synopsis": (d.synopsis or "")[:300],
            "mova_reviews": {"count": agg.review_count, "avg_rating": agg.avg_rating},
        }

    async def now_showing(self) -> dict[str, Any]:
        rows = await self._box_office.fetch_box_office(
            BookingAssistService._last_completed_week_date(), "0"
        )
        self.last_box_office = list(rows[:10])
        return {"this_week_box_office": [f"{r.rank}. {r.title}" for r in rows[:10]]}

    async def showing_cards(self, limit: int = 5) -> list[Any]:
        """박스오피스 상영작 → 카탈로그 상세(포스터·줄거리). 카탈로그에 없는 작품은 건너뛴다."""
        out: list[Any] = []
        for entry in self.last_box_office:
            items = await self._repo.search_movies_by_title([entry.title], 5)
            wanted = MovieTitle(entry.title)
            exact = [i for i in items if wanted.equals(i.title)]
            if not exact:
                continue
            open_year = getattr(entry, "open_year", None)
            pick = next((i for i in exact if open_year and str(i.year) == str(open_year)), exact[0])
            detail = await self._movies.find_by_id(int(pick.id))
            if detail is not None:
                out.append(detail)
            if len(out) >= limit:
                break
        return out


# --- 사실 템플릿(도구 결과 → 문장) ------------------------------------------------------------


def _fact(message: str, name: str, args: dict[str, Any], r: dict[str, Any]) -> str | None:
    if not isinstance(r, dict) or "error" in r:
        return None
    if name == "get_movie_details" and r.get("title"):
        t = r["title"]
        cast, dirs = "·".join(r.get("cast") or []), "·".join(r.get("director") or [])
        if ASK_CAST.search(message):
            return f"『{t}』은(는) {dirs or '감독 미상'} 감독 작품이고, {cast or '출연진 정보 없음'} 등이 출연해요."
        if ASK_PLOT.search(message):
            return f"『{t}』 줄거리: {r.get('synopsis') or '줄거리 정보가 없어요.'}"
        rv = r.get("mova_reviews") or {}
        rev = (
            f"mova 리뷰 {rv.get('count')}건, 평균 별점 {rv.get('avg_rating')}"
            if rv.get("avg_rating") is not None
            else "아직 mova 리뷰는 없어요"
        )
        syn = (r.get("synopsis") or "").split(". ")[0].rstrip(".")
        return (
            f"『{t}』({', '.join(r.get('genres') or [])}) — {syn}. {dirs} 감독, {cast} 출연. {rev}."
        )
    if name == "now_showing":
        top = r.get("this_week_box_office") or []
        return (
            ("지난주 박스오피스 기준 극장 상영작이에요: " + " / ".join(top[:8]))
            if top
            else "박스오피스 정보를 가져오지 못했어요."
        )
    if name == "search_movie":
        if r.get("found"):
            newer = [x for x in r.get("same_name_titles_newest_first") or [] if x != r["found"]]
            return f"카탈로그에서 『{r['found']}』을(를) 찾았어요." + (
                f" 같은 이름의 다른 작품(최신순): {', '.join(newer[:4])}" if newer else ""
            )
        if r.get("candidates"):
            return (
                "비슷한 제목이 여러 편이에요: " + ", ".join(r["candidates"]) + ". 어떤 작품인가요?"
            )
        return f"카탈로그에서 '{args.get('title', '')}'을(를) 찾지 못했어요. 제목을 다시 알려주시겠어요?"
    return None


def compose_facts(message: str, results: list[dict[str, Any]]) -> str | None:
    """이번 턴의 도구 결과를 호출 순서대로 문장화. 결과가 없으면 None(호출자가 잡담 경로로)."""
    lines: list[str] = []
    for r in results:
        line = _fact(message, r["name"], r.get("arguments") or {}, r.get("result") or {})
        if line and line not in lines:
            lines.append(line)
    return "\n".join(lines) or None


def wants_review_summary(message: str, results: list[dict[str, Any]]) -> str | None:
    """get_movie_details로 끝났는데 출연진·줄거리 질문이 아니면("어때?") 기존 평가 트랙(리뷰 요약 문장)이
    더 낫다 — 그 작품 제목을 돌려준다. 아니면 None."""
    last = next((r for r in reversed(results) if r["name"] == "get_movie_details"), None)
    if last is None or ASK_CAST.search(message) or ASK_PLOT.search(message):
        return None
    result = last.get("result") or {}
    return (last.get("arguments") or {}).get("title") if result.get("title") else None
