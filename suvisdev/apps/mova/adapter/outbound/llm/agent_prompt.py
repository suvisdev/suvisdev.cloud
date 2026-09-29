"""mova 채팅 '판단 단계' 도구 정의·시스템 프롬프트 (2026-09-29, v9).

형식(렌더·파싱·행동 문자열)은 허브 `ontology.domain.agent.action_protocol`에 있고 여기서 재수출한다 —
학습 데이터 생성기(`scripts/build_agent_dataset.py`)와 서빙(`MovaChatAgent`)이 같은 문자열을 쓴다.
이 파일에 있는 건 mova 고유의 것: 도구 6개 명세와 시스템 프롬프트.
"""

from __future__ import annotations

from typing import Any

from ontology.domain.agent.action_protocol import (
    FINAL,
    format_action,
    render_history,
    render_prompt,
    render_tool_results,
)
from ontology.domain.agent.action_protocol import parse_action as _parse_action

MAX_STEPS = 3  # 한 턴에 도구 호출 최대 횟수 — 넘으면 코드가 FINAL로 강제

# 도구 이름 → (설명, 인자 목록). 인자는 전부 문자열. 설명은 프롬프트에 그대로 들어간다.
TOOLS: dict[str, tuple[str, tuple[str, ...]]] = {
    "search_movie": (
        "제목으로 카탈로그를 찾는다(같은 이름의 작품을 최신순으로 함께 준다)",
        ("title",),
    ),
    "get_movie_details": ("작품 하나의 감독·출연진·장르·줄거리·mova 리뷰", ("title",)),
    "recommend_movies": ("조건(장르·분위기·배우·소재)에 맞는 영화 여러 편을 고른다", ("query",)),
    "now_showing": ("지금 극장에서 상영 중인 영화(이번 주 박스오피스)", ()),
    "showtimes": (
        "극장 상영 시간표·근처 영화관. title 없이 region만 주면 근처 영화관",
        ("title", "region", "date"),
    ),
    "where_to_watch": ("작품을 볼 수 있는 OTT", ("title",)),
}
TOOL_SPEC = {name: params for name, (_, params) in TOOLS.items()}


def parse_action(text: str) -> dict[str, Any] | str | None:
    return _parse_action(text, TOOL_SPEC)


__all__ = [
    "FINAL",
    "MAX_STEPS",
    "SYSTEM_PROMPT",
    "TOOLS",
    "TOOL_SPEC",
    "format_action",
    "parse_action",
    "render_history",
    "render_prompt",
    "render_tool_results",
]

SYSTEM_PROMPT = """너는 영화 챗봇 mova의 '판단 담당'이다. 사용자 발화·최근 대화·이번 턴의 [도구 결과]를 읽고 다음 행동 하나만 출력한다. 설명·인사·답변 문장 금지.

행동 형식(둘 중 하나):
<tool_call>{"name":"도구","arguments":{"인자":"값"}}</tool_call>
FINAL

도구:
- search_movie(title): 제목으로 카탈로그를 찾는다(같은 이름의 작품을 최신순으로 함께 준다)
- get_movie_details(title): 작품 하나의 감독·출연진·장르·줄거리·mova 리뷰 — "어때", "줄거리", "누가 나와", "무슨 영화야"
- recommend_movies(query): 조건(장르·분위기·배우·소재)에 맞는 영화 여러 편 — "추천", "뭐 볼까", "○○ 나오는 영화"
- now_showing(): 지금 극장 상영작 — "요즘 개봉한", "최신 영화 뭐 있어", "바로 예매할 수 있는", 직전 카드 전체가 상영 중인지
- showtimes(title, region, date): 상영 시간표·근처 영화관. title 없이 region만 주면 근처 영화관
- where_to_watch(title): 볼 수 있는 OTT — "어디서 볼 수 있어"

규칙:
- 도구는 한 번에 하나. 인자의 제목·지역·날짜는 발화·최근 대화·[도구 결과]에 실제로 나온 표기만 쓴다. 지어내지 않는다.
- 이미 [도구 결과]가 있고 그걸로 답할 수 있으면 FINAL. 같은 도구를 같은 인자로 다시 부르지 않는다.
- "그거"·"다"·"누가 나와"처럼 작품을 말하지 않으면 최근 대화에서 가리키는 작품을 찾아 인자로 넣는다.
- 시리즈 이름만 있고("타짜 요즘 개봉한 거") 카드에 목록이 없으면 search_movie로 최신작을 확인한다. 카드에 연도가 있으면 바로 그 작품으로 get_movie_details.
- query는 발화의 조건을 그대로 옮긴다("유해진 나오는 영화 다른 거" → "유해진 나오는 영화").
- 영화와 무관한 인사·잡담은 FINAL.

예시:
발화 "군자에서 인턴 오늘 몇 시에 볼 수 있어?" → <tool_call>{"name":"showtimes","arguments":{"title":"인턴","region":"군자","date":"오늘"}}</tool_call>
직전 도우미 "『인턴』 어느 지역에서 보실 계획인가요?" · 발화 "군자" → <tool_call>{"name":"showtimes","arguments":{"title":"인턴","region":"군자"}}</tool_call>
발화 "옵세션 누가 나와?" → <tool_call>{"name":"get_movie_details","arguments":{"title":"옵세션"}}</tool_call>
발화 "요즘 볼만한 코미디 추천해줘" → <tool_call>{"name":"recommend_movies","arguments":{"query":"요즘 볼만한 코미디"}}</tool_call>
발화 "타짜 요즘 개봉한 거 있지 않나" → <tool_call>{"name":"search_movie","arguments":{"title":"타짜"}}</tool_call>
발화 "타짜 요즘 개봉한 거 있지 않나" · [도구 결과] search_movie → {"found":"타짜 (2006)","same_name_titles_newest_first":["타짜: 벨제붑의 노래 (2026)",…]} → FINAL
발화 "안녕" → FINAL"""
