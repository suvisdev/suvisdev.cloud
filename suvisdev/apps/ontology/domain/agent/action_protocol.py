"""에이전트 행동 프로토콜 — 판단 모델의 입력 문자열과 출력 형식 (2026-09-29, 허브 공용).

판단 모델은 발화·최근 대화·이번 턴의 도구 결과를 읽고 **다음 행동 하나**만 낸다:
`<tool_call>{"name":…,"arguments":{…}}</tool_call>` 또는 `FINAL`. 사실 문장은 모델이 쓰지 않는다.

여기 함수들은 mova v9 학습 데이터(`scripts/build_agent_dataset.py`)를 만든 것과 **같은 문자열**을 낸다 —
바꾸면 학습 분포와 서빙 분포가 어긋난다. 도구 목록·시스템 프롬프트는 앱(에이전트)마다 다르고
여기엔 형식만 있다. 의존성 0.
"""

from __future__ import annotations

import json
import re
from typing import Any

HISTORY_TURNS = 4
HISTORY_CHARS = 160
RESULT_CHARS = 400
FINAL = "FINAL"

# 도구 이름 → 허용 인자 이름들. parse_action이 이 목록 밖의 도구·인자를 버린다.
ToolSpec = dict[str, tuple[str, ...]]


def render_history(history: list[dict[str, str]]) -> str:
    lines = []
    for m in history[-HISTORY_TURNS:]:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        who = "사용자" if m.get("role") == "user" else "도우미"
        lines.append(f"{who}: {content[:HISTORY_CHARS]}")
    return "\n".join(lines)


def render_tool_results(results: list[dict[str, Any]]) -> str:
    """이번 턴에 이미 부른 도구와 그 결과 — [{"name","arguments","result"}]."""
    lines = []
    for r in results:
        args = json.dumps(r.get("arguments") or {}, ensure_ascii=False)
        body = json.dumps(r.get("result"), ensure_ascii=False)[:RESULT_CHARS]
        lines.append(f"{r['name']}({args}) → {body}")
    return "\n".join(lines)


def render_prompt(
    message: str, history: list[dict[str, str]], results: list[dict[str, Any]] | None = None
) -> str:
    parts = []
    rendered = render_history(history)
    if rendered:
        parts.append(f"[최근 대화]\n{rendered}")
    parts.append(f"[발화]\n{message}")
    if results:
        parts.append(f"[도구 결과]\n{render_tool_results(results)}")
    return "\n\n".join(parts)


def format_action(action: dict[str, Any] | str) -> str:
    """정답·모델 출력 문자열. dict면 도구 호출, "FINAL"이면 그대로."""
    if action == FINAL:
        return FINAL
    assert isinstance(action, dict)
    return (
        "<tool_call>"
        + json.dumps(action, ensure_ascii=False, separators=(",", ":"))
        + "</tool_call>"
    )


_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def parse_action(text: str, tools: ToolSpec) -> dict[str, Any] | str | None:
    """모델 출력 → {"name","arguments"} | "FINAL" | None(형식 아님). 호출이 여럿이면 첫 번째만."""
    m = _CALL.search(text or "")
    if m:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return None
        name = data.get("name")
        if name not in tools:
            return None
        raw_args = data.get("arguments") or {}
        allowed = tools[name]
        args = {
            k: str(v).strip()
            for k, v in raw_args.items()
            if k in allowed and isinstance(v, str | int | float) and str(v).strip()
        }
        return {"name": name, "arguments": args}
    if re.search(r"\bFINAL\b", text or ""):
        return FINAL
    return None


def normalize(text: str | None) -> str:
    """근거 대조용 정규화 — 공백·따옴표·괄호·연도 제거, 소문자."""
    return re.sub(r"[\s()\[\]『』'\"·:,.!?~]|\d{4}", "", text or "").lower()


def is_grounded(value: str, context: str) -> bool:
    """인자 값이 발화·대화·도구 결과 어딘가에 실제로 나오는가(제목·지역 창작 방지)."""
    v = normalize(value)
    return not v or v in context
