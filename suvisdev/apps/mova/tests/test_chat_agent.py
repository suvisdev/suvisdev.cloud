"""MovaChatAgent — 도구 6개·사실 템플릿·ChatInteractor 에이전트 분기 (2026-09-29, v9)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mova.app.use_cases.chat_agent import (
    MovaChatAgent,
    compose_facts,
    parse_rating,
    wants_review_summary,
)
from ontology.app.ports.output.judge_port import JudgeError, JudgePort
from ontology.domain.agent.action_protocol import FINAL, format_action


class _Judge(JudgePort):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)

    async def decide(self, system: str, prompt: str) -> str:
        if not self.outputs:
            raise JudgeError("down")
        return self.outputs.pop(0)


@dataclass
class _Item:
    id: str
    title: str
    year: str


@dataclass
class _Actor:
    name: str
    character_id: int | None


@dataclass
class _Detail:
    title: str
    release_year: int
    genres: list[str]
    synopsis: str
    actors: list[_Actor]


@dataclass
class _Agg:
    review_count: int
    avg_rating: float | None


@dataclass
class _Box:
    rank: int
    title: str


class _Repo:
    async def search_movies_by_title(self, terms: list[str], limit: int) -> list[_Item]:
        t = terms[0]
        if "타짜" in t:
            return [_Item("1", "타짜", "2006"), _Item("2", "타짜: 벨제붑의 노래", "2026")]
        if "밤의 해변" in t:
            return [_Item("3", "밤의 해변에서 혼자", "2017")]
        return []


class _Movies:
    async def find_by_id(self, movie_id: int) -> _Detail:
        return _Detail(
            "밤의 해변에서 혼자",
            2017,
            ["드라마"],
            "여배우 영희가 강릉을 오가며 자신을 돌아본다. 긴 이야기.",
            [_Actor("홍상수", None), _Actor("김민희", 1), _Actor("권해효", 2)],
        )


class _Reviews:
    async def aggregate_for_movie(self, movie_id: int, *, excerpt_limit: int = 3) -> _Agg:
        return _Agg(0, None)


class _BoxOffice:
    async def fetch_box_office(self, target_date: str | None, week_gb: str) -> list[_Box]:
        return [_Box(1, "암살자(들)"), _Box(2, "타짜: 벨제붑의 노래")]


def _agent(outputs: list[str]) -> MovaChatAgent:
    return MovaChatAgent(
        judge=_Judge(outputs),
        repository=_Repo(),
        movies=_Movies(),
        reviews=_Reviews(),
        box_office=_BoxOffice(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_cast_question_uses_details_tool_and_template():
    hist = [{"role": "user", "content": "밤의 해변에서 혼자 어디서 볼수 있나"}]
    agent = _agent(
        [
            format_action(
                {"name": "get_movie_details", "arguments": {"title": "밤의 해변에서 혼자"}}
            ),
            FINAL,
        ]
    )
    d = await agent.decide("누가나와", hist, trace_id="t")
    assert d.terminal is None and d.results[0]["result"]["director"] == ["홍상수"]
    reply = compose_facts("누가나와", d.results)
    assert (
        reply
        == "『밤의 해변에서 혼자 (2017)』은(는) 홍상수 감독 작품이고, 김민희·권해효 등이 출연해요."
    )
    assert wants_review_summary("누가나와", d.results) is None  # 출연진 질문은 템플릿이 답


@pytest.mark.asyncio
async def test_how_is_it_question_hands_over_to_review_summary():
    agent = _agent(
        [
            format_action(
                {"name": "get_movie_details", "arguments": {"title": "밤의 해변에서 혼자"}}
            ),
            FINAL,
        ]
    )
    d = await agent.decide("밤의 해변에서 혼자 어때?", [], trace_id="t")
    assert wants_review_summary("밤의 해변에서 혼자 어때?", d.results) == "밤의 해변에서 혼자"


@pytest.mark.asyncio
async def test_franchise_latest_via_search_lists_newest_first():
    agent = _agent([format_action({"name": "search_movie", "arguments": {"title": "타짜"}}), FINAL])
    d = await agent.decide("타짜 요즘 개봉한거 있지 않나", [], trace_id="t")
    r = d.results[0]["result"]
    assert (
        r["found"] == "타짜 (2006)"
        and r["same_name_titles_newest_first"][0] == "타짜: 벨제붑의 노래 (2026)"
    )
    assert "타짜: 벨제붑의 노래 (2026)" in (
        compose_facts("타짜 요즘 개봉한거 있지 않나", d.results) or ""
    )


@pytest.mark.asyncio
async def test_now_showing_and_terminal_showtimes():
    agent = _agent([format_action({"name": "now_showing", "arguments": {}}), FINAL])
    d = await agent.decide("최신 개봉영화 뭐있는지 찾아봐", [], trace_id="t")
    assert compose_facts("최신 개봉영화 뭐있는지 찾아봐", d.results).startswith(
        "지난주 박스오피스 기준 극장 상영작이에요: 1. 암살자(들)"
    )

    agent = _agent(
        [
            format_action(
                {
                    "name": "showtimes",
                    "arguments": {"title": "타짜", "region": "군자역", "date": "오늘"},
                }
            )
        ]
    )
    d = await agent.decide("군자역에서 타짜 오늘 몇 시에 해?", [], trace_id="t")
    assert d.terminal == {
        "name": "showtimes",
        "arguments": {"title": "타짜", "region": "군자역", "date": "오늘"},
    }


@pytest.mark.asyncio
async def test_judge_failure_raises_for_fallback():
    with pytest.raises(JudgeError):
        await _agent([]).decide("안녕", [], trace_id="t")


def test_compose_facts_returns_none_without_results():
    assert compose_facts("안녕", []) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4", 4.0),
        ("3.5", 3.5),
        ("4점", 4.0),
        ("3.7", 3.5),  # 0.5 단위 반올림(3.7→3.5)
        ("3.8", 4.0),  # 3.8→4.0
        ("6", 5.0),  # 상한 클램프
        ("0", 0.5),  # 하한 클램프
        (None, None),
        ("", None),
        ("좋았어", None),  # 숫자 없음 → 별점 없이 봤어요만
    ],
)
def test_parse_rating(raw, expected):
    assert parse_rating(raw) == expected


@pytest.mark.asyncio
async def test_mark_watched_returns_terminal_action():
    # 직전 카드에 나온 작품을 지시어로 가리키고 별점을 말함 — title 근거 가드 통과, 터미널로 반환
    hist = [{"role": "assistant", "content": "[추천 카드] 1.『밤의 해변에서 혼자』(2017)"}]
    agent = _agent(
        [
            format_action(
                {
                    "name": "mark_watched",
                    "arguments": {"title": "밤의 해변에서 혼자", "rating": "4"},
                }
            )
        ]
    )
    d = await agent.decide("그거 봤어, 4점", hist, trace_id="t")
    assert d.terminal == {
        "name": "mark_watched",
        "arguments": {"title": "밤의 해변에서 혼자", "rating": "4"},
    }


@pytest.mark.asyncio
async def test_v10_taste_tools_return_terminal():
    # recommend_for_me: query는 자유 문장이라 근거 가드 없음
    agent = _agent([format_action({"name": "recommend_for_me", "arguments": {"query": "내 취향"}})])
    d = await agent.decide("내 취향에 맞는 거 추천해줘", [], trace_id="t")
    assert d.terminal == {"name": "recommend_for_me", "arguments": {"query": "내 취향"}}

    # similar_to: title은 발화에 있어야 근거 가드 통과
    agent = _agent([format_action({"name": "similar_to", "arguments": {"title": "기생충"}})])
    d = await agent.decide("기생충 같은 영화 추천해줘", [], trace_id="t")
    assert d.terminal == {"name": "similar_to", "arguments": {"title": "기생충"}}

    # taste_profile: 인자 없음
    agent = _agent([format_action({"name": "taste_profile", "arguments": {}})])
    d = await agent.decide("내 취향이 뭐야", [], trace_id="t")
    assert d.terminal == {"name": "taste_profile", "arguments": {}}


@pytest.mark.asyncio
async def test_year_suffix_is_stripped_before_title_resolution():
    agent = _agent(
        [
            format_action(
                {"name": "search_movie", "arguments": {"title": "타짜: 벨제붑의 노래 (2026)"}}
            ),
            FINAL,
        ]
    )
    d = await agent.decide("타짜 요즘 개봉한거 있지 않나", [], trace_id="t")
    r = d.results[0]["result"]
    assert r.get("found", "").startswith("타짜: 벨제붑의 노래") or "타짜: 벨제붑의 노래 (2026)" in (
        r.get("candidates") or []
    )
