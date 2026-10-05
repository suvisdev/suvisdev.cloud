"""PORTFOLIO_LLM_BACKEND 스위치 — 기본은 EXAONE→Gemini 폴백, gemini면 Gemini(재시도 포함)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.llm.fallback_hub_llm_adapter import (  # noqa: E402
    FallbackHubLlmAdapter,
)
from ontology.adapter.outbound.llm.retry_hub_llm_adapter import RetryHubLlmAdapter  # noqa: E402
from ontology.dependencies.portfolio_chat_provider import get_portfolio_llm_port  # noqa: E402


class PortfolioLlmBackendSwitchTests(unittest.TestCase):
    def test_unset_defaults_to_exaone_with_gemini_fallback(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("PORTFOLIO_LLM_BACKEND", None)
            self.assertIsInstance(get_portfolio_llm_port(), FallbackHubLlmAdapter)

    def test_gemini_selects_gemini_only(self) -> None:
        with patch.dict(
            "os.environ", {"PORTFOLIO_LLM_BACKEND": "gemini", "PORTFOLIO_LLM_FALLBACK_URL": ""}
        ):
            self.assertIsInstance(get_portfolio_llm_port(), RetryHubLlmAdapter)

    def test_gemini_is_case_and_space_insensitive(self) -> None:
        with patch.dict(
            "os.environ", {"PORTFOLIO_LLM_BACKEND": "  GEMINI ", "PORTFOLIO_LLM_FALLBACK_URL": ""}
        ):
            self.assertIsInstance(get_portfolio_llm_port(), RetryHubLlmAdapter)

    def test_unknown_value_falls_back_to_default(self) -> None:
        with patch.dict("os.environ", {"PORTFOLIO_LLM_BACKEND": "claude"}):
            self.assertIsInstance(get_portfolio_llm_port(), FallbackHubLlmAdapter)


if __name__ == "__main__":
    unittest.main()
