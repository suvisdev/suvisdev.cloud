"""판단 모델 출력 포트 — 에이전트 루프가 "다음 행동"을 물을 때 쓰는 LLM 호출 (2026-09-29)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class JudgeError(Exception):
    """판단 모델 호출 실패(Ollama 다운·타임아웃). 루프는 이걸 받으면 판단을 포기한다(호출자가 폴백)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class JudgePort(ABC):
    @abstractmethod
    async def decide(self, system: str, prompt: str) -> str:
        """system + 렌더된 프롬프트 → 모델 원문(`<tool_call>…</tool_call>` 또는 `FINAL`)."""
        ...
