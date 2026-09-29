"""JudgePort 구현 — 학습한 판단 모델(기본 `mova-agent-v9`, EXAONE 3.5 2.4B LoRA, Ollama CPU)을 부른다 (2026-09-29).

같은 OllamaClient(전화기)를 쓰되 JSON 모드가 아니라 원문 생성이다 — 출력이 `<tool_call>{…}</tool_call>`
또는 `FINAL`. temperature 0, num_ctx 4096(최근 대화 4턴 + 도구 결과 3개까지 넉넉). 학습 템플릿과
같은 [|system|]/[|user|] 렌더는 Ollama Modelfile(코랩 7번 셀)이 보장한다.
"""

from __future__ import annotations

import asyncio
import os

from core.lol.ollama_client import OllamaClient, OllamaClientError
from ontology.app.ports.output.judge_port import JudgeError, JudgePort

_DEFAULT_MODEL = "mova-agent-v9"


class OllamaJudgeAdapter(JudgePort):
    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient(
            model=os.getenv("MOVA_AGENT_MODEL", _DEFAULT_MODEL),
            timeout=float(os.getenv("MOVA_AGENT_TIMEOUT_S", "30")),
        )

    async def decide(self, system: str, prompt: str) -> str:
        try:
            # 동기 httpx 클라이언트 — 이벤트 루프를 막지 않게 스레드로 넘긴다.
            return await asyncio.to_thread(
                self._client.generate, prompt, system=system, temperature=0, num_ctx=4096
            )
        except OllamaClientError as e:
            raise JudgeError(e.detail) from e
