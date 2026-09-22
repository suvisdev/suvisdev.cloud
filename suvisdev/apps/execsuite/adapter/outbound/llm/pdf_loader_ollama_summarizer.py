"""EXAONE(Ollama, T1MidFakerOrchestrator) 기반 PdfSummarizerPort 구현체."""

from __future__ import annotations

import asyncio

from core.lol.t1_mid_faker_orchestrator import FakerOrchestratorError, T1MidFakerOrchestrator
from execsuite.app.ports.output.pdf_loader_summarizer_port import PdfSummarizerPort

_SYSTEM_PROMPT = (
    "너는 문서 요약 도우미다. 주어진 텍스트의 핵심 내용을 한국어로 5문장 "
    "이내로 간결하게 요약해라. 불필요한 서두 없이 요약문만 출력해라."
)

# exaone3.5:7.8b 컨텍스트 여유를 위한 안전한 입력 상한 — PdfLoader가 반환한 원문
# 전체를 그대로 프롬프트에 넣으면 대용량 PDF에서 컨텍스트 초과 위험이 있어
# 앞부분만 잘라 넣는다(전체 요약이 아닌 앞부분 요약이 되는 트레이드오프는 감수).
_MAX_INPUT_CHARS = 12000


class OllamaExaonePdfSummarizer(PdfSummarizerPort):
    def __init__(self) -> None:
        # keep_alive "0": 요약 직후 7.8B를 VRAM에서 내린다 — 상주하면 노트북 8GB에서
        # 채팅용 bge-m3·라우터 2.4B가 밀려난다(2026-09-17 실측). 대가는 요청마다 로드 수 초.
        self._orchestrator = T1MidFakerOrchestrator(keep_alive="0")

    async def summarize(self, text: str) -> str:
        truncated = text[:_MAX_INPUT_CHARS]
        try:
            return await asyncio.to_thread(
                self._orchestrator.generate,
                truncated,
                system=_SYSTEM_PROMPT,
            )
        except FakerOrchestratorError as e:
            raise ValueError(f"요약 생성 실패: {e.detail}") from e
