"""포트폴리오 채팅 LLM 재시도·노트북 7.8B 대체(2026-10-06).

① 일시 오류(502·503·429·504)는 한 번 더 부른다 ② 요청 오류(400)는 다시 부르지 않는다
③ 재시도도 실패하면 오류를 그대로 올린다 ④ PORTFOLIO_LLM_FALLBACK_URL이 있으면 Gemini(재시도 포함)가
끝내 실패할 때 그 주소의 EXAONE 7.8B로 답한다 — 없으면(집컴) 7.8B를 아예 만들지 않는다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.llm import retry_hub_llm_adapter as retry_module  # noqa: E402
from ontology.adapter.outbound.llm.exaone_llm_adapter import ExaoneLlmAdapter  # noqa: E402
from ontology.adapter.outbound.llm.fallback_hub_llm_adapter import (  # noqa: E402
    FallbackHubLlmAdapter,
)
from ontology.adapter.outbound.llm.retry_hub_llm_adapter import RetryHubLlmAdapter  # noqa: E402
from ontology.app.ports.output.hub_llm_port import HubLlmPort  # noqa: E402
from ontology.app.ports.output.hub_rag_errors import HubRagError  # noqa: E402
from ontology.dependencies.portfolio_chat_provider import get_portfolio_llm_port  # noqa: E402


class _Flaky(HubLlmPort):
    """정해진 상태 코드로 몇 번 실패한 뒤 성공한다."""

    def __init__(self, failures: list[int]) -> None:
        self.failures = list(failures)
        self.calls = 0

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls += 1
        if self.failures:
            raise HubRagError("일시 오류", status_code=self.failures.pop(0))
        return "답변"


class RetryHubLlmAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        sleep = patch.object(retry_module.asyncio, "sleep", new=AsyncMock())
        sleep.start()
        self.addCleanup(sleep.stop)

    async def test_retries_once_on_gemini_overload(self) -> None:
        inner = _Flaky([502])
        self.assertEqual(await RetryHubLlmAdapter(inner).generate("q"), "답변")
        self.assertEqual(inner.calls, 2)

    async def test_retries_on_each_transient_status(self) -> None:
        for status in (429, 502, 503, 504):
            inner = _Flaky([status])
            self.assertEqual(await RetryHubLlmAdapter(inner).generate("q"), "답변")
            self.assertEqual(inner.calls, 2, status)

    async def test_does_not_retry_bad_request(self) -> None:
        inner = _Flaky([400])
        with self.assertRaises(HubRagError) as cm:
            await RetryHubLlmAdapter(inner).generate("q")
        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(inner.calls, 1)

    async def test_raises_after_last_attempt(self) -> None:
        inner = _Flaky([503, 503])
        with self.assertRaises(HubRagError) as cm:
            await RetryHubLlmAdapter(inner).generate("q")
        self.assertEqual(cm.exception.status_code, 503)
        self.assertEqual(inner.calls, 2)


class PortfolioFallbackWiringTests(unittest.TestCase):
    def test_gemini_without_fallback_url_is_retry_only(self) -> None:
        env = {"PORTFOLIO_LLM_BACKEND": "gemini", "PORTFOLIO_LLM_FALLBACK_URL": ""}
        with patch.dict("os.environ", env):
            self.assertIsInstance(get_portfolio_llm_port(), RetryHubLlmAdapter)

    def test_gemini_with_fallback_url_adds_exaone_at_that_url(self) -> None:
        env = {
            "PORTFOLIO_LLM_BACKEND": "gemini",
            "PORTFOLIO_LLM_FALLBACK_URL": "http://host.docker.internal:11434/",
        }
        with patch.dict("os.environ", env):
            port = get_portfolio_llm_port()
        self.assertIsInstance(port, FallbackHubLlmAdapter)
        self.assertIsInstance(port._primary, RetryHubLlmAdapter)  # noqa: SLF001
        fallback = port._fallback  # noqa: SLF001
        self.assertIsInstance(fallback, ExaoneLlmAdapter)
        self.assertEqual(
            fallback._orchestrator._base_url,  # noqa: SLF001
            "http://host.docker.internal:11434",
        )


class GeminiThenExaoneTests(unittest.IsolatedAsyncioTestCase):
    async def test_exaone_answers_when_gemini_keeps_failing(self) -> None:
        with patch.object(retry_module.asyncio, "sleep", new=AsyncMock()):
            gemini = _Flaky([503, 503])
            exaone = _Flaky([])
            port = FallbackHubLlmAdapter(primary=RetryHubLlmAdapter(gemini), fallback=exaone)
            self.assertEqual(await port.generate("q"), "답변")
        self.assertEqual(gemini.calls, 2)
        self.assertEqual(exaone.calls, 1)


if __name__ == "__main__":
    unittest.main()
