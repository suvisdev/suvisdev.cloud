"""올라마 임베딩 어댑터(2026-10-07).

- keep_alive 를 실어 보내는지 — 빠지면 올라마 기본 5분 뒤 bge-m3 가 내려간다.
- OLLAMA_EMBED_URL 이 있으면 그 주소(집컴 올라마 고정), 없으면 OLLAMA_BASE_URL(중계기).
"""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.llm import ollama_embedding_adapter as mod  # noqa: E402


def test_embed_sends_keep_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        mod.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    adapter = mod.OllamaEmbeddingAdapter(base_url="http://ollama", keep_alive="-1m")
    assert asyncio.run(adapter.embed("안녕")) == [0.1, 0.2]
    assert sent == {"model": adapter._model, "input": "안녕", "keep_alive": "-1m"}


@pytest.mark.parametrize(
    ("embed_url", "expected"),
    [("http://desk:11434", "http://desk:11434"), ("", "http://relay:11435")],
)
def test_embed_url_overrides_base(
    monkeypatch: pytest.MonkeyPatch, embed_url: str, expected: str
) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://relay:11435")
    monkeypatch.setenv("OLLAMA_EMBED_URL", embed_url)
    try:
        assert importlib.reload(mod).OllamaEmbeddingAdapter()._base_url == expected
    finally:
        monkeypatch.undo()
        importlib.reload(mod)
