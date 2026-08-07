"""get_hub_embedding_port()의 EMBEDDING_BACKEND 스위치 + GeminiEmbeddingAdapter 계약 테스트.

EC2엔 Ollama가 없어 이 스위치를 안 걸면 벡터 검색 경로가 조용히 죽는다
(2026-08-07 프로덕션 실측). 스위치가 실제로 어댑터를 갈아끼우는지 고정한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.llm.gemini_embedding_adapter import (  # noqa: E402
    GeminiEmbeddingAdapter,
)
from ontology.adapter.outbound.llm.ollama_embedding_adapter import (  # noqa: E402
    OllamaEmbeddingAdapter,
)
from ontology.app.ports.output.hub_rag_errors import HubRagError  # noqa: E402
from ontology.app.ports.output.knowledge_embedding_port import EMBEDDING_DIM  # noqa: E402
from ontology.dependencies.hub_rag_provider import get_hub_embedding_port  # noqa: E402


class EmbeddingBackendSwitchTests(unittest.TestCase):
    def test_defaults_to_ollama_when_unset(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("EMBEDDING_BACKEND", None)
            self.assertIsInstance(get_hub_embedding_port(), OllamaEmbeddingAdapter)

    def test_gemini_backend_selected(self) -> None:
        with patch.dict("os.environ", {"EMBEDDING_BACKEND": "gemini"}):
            self.assertIsInstance(get_hub_embedding_port(), GeminiEmbeddingAdapter)

    def test_backend_value_is_case_insensitive(self) -> None:
        with patch.dict("os.environ", {"EMBEDDING_BACKEND": "  GEMINI  "}):
            self.assertIsInstance(get_hub_embedding_port(), GeminiEmbeddingAdapter)

    def test_unknown_backend_falls_back_to_ollama(self) -> None:
        with patch.dict("os.environ", {"EMBEDDING_BACKEND": "nonsense"}):
            self.assertIsInstance(get_hub_embedding_port(), OllamaEmbeddingAdapter)


class GeminiEmbeddingAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_api_key_raises_hub_rag_error(self) -> None:
        adapter = GeminiEmbeddingAdapter()
        fake_keymaker = type("_K", (), {"gemini_ready": False})()

        with patch(
            "core.matrix.vauly_keymaker_secret_manager.get_keymaker",
            return_value=fake_keymaker,
        ):
            with self.assertRaises(HubRagError) as ctx:
                await adapter.embed("아무 텍스트")

        self.assertEqual(ctx.exception.status_code, 503)

    async def test_requests_column_dimension(self) -> None:
        """저장 컬럼이 Vector(768)이라 output_dimensionality를 반드시 넘겨야 한다."""
        adapter = GeminiEmbeddingAdapter()
        fake_keymaker = type("_K", (), {"gemini_ready": True})()
        captured: dict = {}

        def _fake_embed_content(**kwargs):
            captured.update(kwargs)
            return {"embedding": [0.1] * EMBEDDING_DIM}

        with (
            patch(
                "core.matrix.vauly_keymaker_secret_manager.get_keymaker",
                return_value=fake_keymaker,
            ),
            patch("google.generativeai.embed_content", _fake_embed_content),
        ):
            vector = await adapter.embed("감동적인 드라마")

        self.assertEqual(len(vector), EMBEDDING_DIM)
        self.assertEqual(captured["output_dimensionality"], EMBEDDING_DIM)

    async def test_empty_embedding_raises(self) -> None:
        adapter = GeminiEmbeddingAdapter()
        fake_keymaker = type("_K", (), {"gemini_ready": True})()

        with (
            patch(
                "core.matrix.vauly_keymaker_secret_manager.get_keymaker",
                return_value=fake_keymaker,
            ),
            patch("google.generativeai.embed_content", lambda **kw: {"embedding": []}),
        ):
            with self.assertRaises(HubRagError):
                await adapter.embed("감동적인 드라마")

    async def test_api_exception_becomes_hub_rag_error(self) -> None:
        """어댑터 밖으로 raw 예외가 새면 HubRagInteractor의 폴백이 안 걸린다."""
        adapter = GeminiEmbeddingAdapter()
        fake_keymaker = type("_K", (), {"gemini_ready": True})()

        def _boom(**kwargs):
            raise RuntimeError("quota exceeded")

        with (
            patch(
                "core.matrix.vauly_keymaker_secret_manager.get_keymaker",
                return_value=fake_keymaker,
            ),
            patch("google.generativeai.embed_content", _boom),
        ):
            with self.assertRaises(HubRagError):
                await adapter.embed("감동적인 드라마")


if __name__ == "__main__":
    unittest.main()
