"""HubLlmPort 재시도 — 일시 오류(할당량·과부하·게이트웨이)면 잠깐 쉬고 한 번 더 부른다.

2026-10-06 실측: 홈 포트폴리오 채팅이 Gemini의 "503 UNAVAILABLE — This model is currently
experiencing high demand"를 그대로 502로 돌려줬다. 이런 오류는 대개 몇 초 안에 풀린다.
요청 자체가 잘못된 경우(400 등)는 다시 불러도 같으므로 재시도하지 않는다.
"""

from __future__ import annotations

import asyncio
import logging

from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


class RetryHubLlmAdapter(HubLlmPort):
    def __init__(self, inner: HubLlmPort, *, attempts: int = 2, delay_s: float = 1.5) -> None:
        self._inner = inner
        self._attempts = max(1, attempts)
        self._delay_s = delay_s

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        for attempt in range(1, self._attempts + 1):
            try:
                return await self._inner.generate(prompt, system=system)
            except HubRagError as e:
                if e.status_code not in RETRYABLE_STATUS or attempt == self._attempts:
                    raise
                logger.warning(
                    "[RetryHubLlmAdapter] 일시 오류 %s → %.1f초 뒤 재시도(%d/%d) | detail=%s",
                    e.status_code,
                    self._delay_s,
                    attempt + 1,
                    self._attempts,
                    e.detail,
                )
                await asyncio.sleep(self._delay_s)
        raise AssertionError("unreachable")  # pragma: no cover
