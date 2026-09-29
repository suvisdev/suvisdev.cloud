"""AgentLoop — 근거 가드·반복 차단·호출 예산·터미널 도구 (2026-09-29)."""

from __future__ import annotations

import pytest

from ontology.app.agent.agent_loop import AgentLoop, Tool
from ontology.app.ports.output.judge_port import JudgePort
from ontology.domain.agent.action_protocol import FINAL, format_action, parse_action


class _ScriptedJudge(JudgePort):
    """호출 순서대로 정해진 출력을 낸다 — 프롬프트에 무엇이 들어갔는지도 기록."""

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    async def decide(self, system: str, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.outputs.pop(0) if self.outputs else FINAL


async def _details(title: str = "") -> dict:
    return {"title": f"{title} (2017)", "cast": ["김민희"], "director": ["홍상수"]}


def _loop(judge: JudgePort, max_steps: int = 3) -> AgentLoop:
    return AgentLoop(
        judge=judge,
        system_prompt="sys",
        tools=[
            Tool("get_movie_details", ("title",), _details, grounded=("title",)),
            Tool("now_showing", (), lambda: _now()),
            Tool("recommend_movies", ("query",), None),
        ],
        max_steps=max_steps,
    )


async def _now() -> dict:
    return {"this_week_box_office": ["1. 타짜: 벨제붑의 노래"]}


@pytest.mark.asyncio
async def test_data_tool_then_final_feeds_result_back_to_judge():
    judge = _ScriptedJudge(
        [
            format_action(
                {"name": "get_movie_details", "arguments": {"title": "밤의 해변에서 혼자"}}
            ),
            FINAL,
        ]
    )
    hist = [{"role": "user", "content": "밤의 해변에서 혼자 어디서 봐"}]
    d = await _loop(judge).run("누가나와", hist)
    assert d.terminal is None and d.steps == 2
    assert d.results[0]["result"]["cast"] == ["김민희"]
    assert "[도구 결과]" in judge.prompts[1] and "get_movie_details" in judge.prompts[1]


@pytest.mark.asyncio
async def test_terminal_tool_is_returned_not_run():
    judge = _ScriptedJudge(
        [format_action({"name": "recommend_movies", "arguments": {"query": "코미디"}})]
    )
    d = await _loop(judge).run("코미디 영화 추천해줘", [])
    assert d.terminal == {"name": "recommend_movies", "arguments": {"query": "코미디"}}
    assert d.results == [] and d.steps == 1


@pytest.mark.asyncio
async def test_ungrounded_title_is_blocked_and_retried():
    judge = _ScriptedJudge(
        [
            format_action(
                {"name": "get_movie_details", "arguments": {"title": "deerwood"}}
            ),  # 창작
            format_action({"name": "get_movie_details", "arguments": {"title": "데자뷰"}}),
            FINAL,
        ]
    )
    d = await _loop(judge).run("데자뷰는 누가 나오지", [])
    assert "error" in d.results[0]["result"] and d.results[1]["result"]["title"].startswith(
        "데자뷰"
    )
    assert any("근거 없음" in t for t in d.trace)


@pytest.mark.asyncio
async def test_duplicate_call_and_budget_force_final():
    same = format_action({"name": "now_showing", "arguments": {}})
    d = await _loop(_ScriptedJudge([same, same, same])).run("요즘 뭐 해", [])
    assert len(d.results) == 1 and any("반복 호출" in t for t in d.trace)

    calls = [
        format_action({"name": "get_movie_details", "arguments": {"title": t}})
        for t in ("인턴", "옵세션", "파과", "타짜")
    ]
    d = await _loop(_ScriptedJudge(calls), max_steps=3).run("인턴 옵세션 파과 타짜 누가 나와", [])
    assert len(d.results) == 3 and d.trace[-1] == "BUDGET → FINAL"


@pytest.mark.asyncio
async def test_unparseable_output_ends_with_no_results():
    d = await _loop(_ScriptedJudge(["안녕하세요! 무엇을 도와드릴까요?"])).run("안녕", [])
    assert d.terminal is None and d.results == [] and "형식 아님" in d.trace[0]


def test_parse_action_filters_unknown_tools_and_args():
    spec = {"showtimes": ("title", "region", "date")}
    assert parse_action(
        '<tool_call>{"name":"showtimes","arguments":{"title":"인턴","x":"y"}}</tool_call>', spec
    ) == {
        "name": "showtimes",
        "arguments": {"title": "인턴"},
    }
    assert parse_action('<tool_call>{"name":"nope","arguments":{}}</tool_call>', spec) is None
    assert parse_action("FINAL", spec) == FINAL and parse_action("그냥 문장", spec) is None


def test_grounding_accepts_series_head_but_not_invented_title():
    from ontology.domain.agent.action_protocol import is_grounded, normalize

    ctx = normalize("타짜 요즘 개봉한거 있지 않나")
    assert is_grounded(
        "타짜: 벨제붑의 노래 (2026)", ctx
    )  # 앞부분이 대화에 있음 → 카탈로그가 가린다
    assert not is_grounded("탑건: 매버릭", ctx)  # 앞부분조차 없음 → 창작
    assert not is_grounded("deerwood", normalize("데자뷰는 누가 나오지"))
