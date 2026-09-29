"""에이전트 루프 — 판단 모델 ↔ 도구 실행을 예산·가드 안에서 반복한다 (2026-09-29, 허브 공용).

층 이름: 오케스트레이터(허브 전체 두뇌, 미구현) → 에이전트(앱 두뇌, 이 루프를 씀) → 도구 → 클라이언트.
앱은 도구 목록과 시스템 프롬프트만 주고, 판단·가드·예산은 여기 한 곳이다. 09-29 실측에서 7.8B가 학습 없이
두뇌를 맡자 턴당 3~10회 과호출·제목 창작("탑건")·자리표시자 지역("지역명 입력")을 냈다 — 그래서
루프는 모델을 믿지 않고 세 가지를 코드로 막는다: ① 인자 근거(발화·대화·결과에 없는 값 차단) ② 같은
호출 반복 차단 ③ 호출 예산(넘으면 FINAL 강제).

도구는 두 종류다. `run`이 있는 데이터 도구는 여기서 실행해 결과를 다음 판단에 붙인다. `run`이 없는
**터미널 도구**(추천·시간표처럼 기존 트랙이 답까지 만드는 것)는 실행하지 않고 그 행동을 그대로 돌려준다 —
트랙이 저장·응답을 한 번에 처리하므로 루프가 두 번 저장하지 않게.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ontology.app.ports.output.judge_port import JudgeError, JudgePort
from ontology.domain.agent.action_protocol import (
    FINAL,
    ToolSpec,
    is_grounded,
    normalize,
    parse_action,
    render_prompt,
)

logger = logging.getLogger(__name__)

ToolRunner = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class Tool:
    name: str
    params: tuple[str, ...]
    run: ToolRunner | None = None  # None이면 터미널 도구(호출자가 실행)
    grounded: tuple[str, ...] = ()  # 근거 가드를 거는 인자 이름(예: title·region·date)


@dataclass
class AgentDecision:
    """루프 결과. terminal이 있으면 호출자가 그 행동을 실행한다(트랙). 없으면 results로 답을 만든다."""

    terminal: dict[str, Any] | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0
    trace: list[str] = field(default_factory=list)


class AgentLoop:
    def __init__(
        self,
        *,
        judge: JudgePort,
        system_prompt: str,
        tools: list[Tool],
        max_steps: int = 3,
    ) -> None:
        self._judge = judge
        self._system = system_prompt
        self._tools = {t.name: t for t in tools}
        self._spec: ToolSpec = {t.name: t.params for t in tools}
        self._max_steps = max_steps

    async def run(
        self, message: str, history: list[dict[str, str]], *, trace_id: str = "-"
    ) -> AgentDecision:
        """JudgeError는 그대로 올린다 — 호출자가 예전 경로로 폴백할 수 있게."""
        d = AgentDecision()
        context = normalize(message + " ".join(m.get("content") or "" for m in history))
        seen: set[str] = set()
        for step in range(1, self._max_steps + 2):
            if step > self._max_steps:
                d.trace.append("BUDGET → FINAL")
                break
            raw = await self._judge.decide(self._system, render_prompt(message, history, d.results))
            d.steps = step
            action = parse_action(raw, self._spec)
            if action is None:
                d.trace.append(f"형식 아님 → FINAL | {raw.strip()[:80]!r}")
                break
            if action == FINAL:
                d.trace.append("FINAL")
                break
            assert isinstance(action, dict)
            name, args = action["name"], action["arguments"]
            tool = self._tools[name]
            bad = [k for k in tool.grounded if k in args and not is_grounded(args[k], context)]
            if bad:
                # 창작 인자 — 모델에게 알려 주고 한 번 더 판단시킨다(재시도 예산 안에서)
                d.trace.append(f"근거 없음 {name}.{bad[0]}={args[bad[0]]!r}")
                d.results.append(
                    {
                        "name": name,
                        "arguments": args,
                        "result": {
                            "error": f"'{args[bad[0]]}'는 대화에 나온 표기가 아니다. 사용자가 쓴 표기 그대로 다시 호출하라."
                        },
                    }
                )
                continue
            key = name + json.dumps(args, ensure_ascii=False, sort_keys=True)
            if key in seen:
                d.trace.append(f"반복 호출 {name} → FINAL")
                break
            seen.add(key)
            if tool.run is None:
                d.terminal = action
                d.trace.append(f"터미널 {name}({json.dumps(args, ensure_ascii=False)})")
                break
            try:
                result = await tool.run(**args)
            except Exception as e:  # noqa: BLE001 — 도구 장애는 모델에 알리고 계속(한 도구가 죽어도 답은 나가야)
                logger.warning("[AgentLoop] trace=%s 도구 %s 실패: %s", trace_id, name, e)
                result = {"error": str(e)[:120]}
            d.results.append({"name": name, "arguments": args, "result": result})
            context += (
                normalize(json.dumps(result, ensure_ascii=False)) if "error" not in result else ""
            )
            d.trace.append(
                f"{name}({json.dumps(args, ensure_ascii=False)}) → {json.dumps(result, ensure_ascii=False)[:120]}"
            )
        logger.info("[AgentLoop] trace=%s steps=%d %s", trace_id, d.steps, " | ".join(d.trace))
        return d


__all__ = ["AgentDecision", "AgentLoop", "JudgeError", "Tool"]
