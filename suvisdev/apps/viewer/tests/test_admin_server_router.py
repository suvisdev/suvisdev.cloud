"""어드민 "서빙 서버" — NODE_NAME(k8s downward API)을 노트북/집컴으로 바꾸고, 챗봇별 LLM 경로를 판정한다."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from shared.security.require_admin import AdminPrincipal, require_admin  # noqa: E402

from viewer.adapter.inbound.api.v1 import admin_server_router as mod  # noqa: E402
from viewer.adapter.inbound.api.v1.admin_server_router import admin_server_router  # noqa: E402

_ENV = {
    "PORTFOLIO_LLM_BACKEND": "exaone",
    "PORTFOLIO_LLM_OLLAMA_URL": "http://laptop:11436",
    "PORTFOLIO_LLM_MODEL": "exaone3.5:7.8b",
    "MOVA_CHAT_AGENT": "0",
    "MOVA_ORCHESTRATOR_ENABLED": "1",
    "MOVA_ORCHESTRATOR_MODEL": "exaone3.5:2.4b",
    "RECOMMENDATION_BACKEND": "lora",
    "LORA_SERVER_URL": "http://desk:8200",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    _set_up(monkeypatch, laptop=True, lora=True)


def _set_up(monkeypatch: pytest.MonkeyPatch, *, laptop: bool, lora: bool) -> None:
    async def fake_up(url: str) -> bool:
        return laptop if url.startswith("http://laptop") else lora

    monkeypatch.setattr(mod, "_up", fake_up)


def _client(*, admin: bool) -> TestClient:
    app = FastAPI()
    app.include_router(admin_server_router)
    if admin:
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="a")
    return TestClient(app)


@pytest.mark.parametrize(
    ("node", "machine"),
    [("teagy", "노트북"), ("desktop-t89e5id", "집컴"), ("other", "알 수 없음"), ("", "알 수 없음")],
)
def test_machine_from_node_name(monkeypatch: pytest.MonkeyPatch, node: str, machine: str) -> None:
    monkeypatch.setenv("NODE_NAME", node)
    res = _client(admin=True).get("/admin/server")
    assert res.status_code == 200
    assert (res.json()["node"], res.json()["machine"]) == (node, machine)


def test_requires_admin() -> None:
    assert _client(admin=False).get("/admin/server").status_code == 401


def _targets() -> list[str]:
    return [r["target"] for r in _client(admin=True).get("/admin/server").json()["chatbots"]]


def test_all_up() -> None:
    assert _targets() == [
        "노트북 GPU · exaone3.5:7.8b",
        "노트북 GPU · exaone3.5:2.4b",
        "집컴 GPU · lora-server",
    ]


def test_laptop_gpu_down_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_up(monkeypatch, laptop=False, lora=False)
    assert _targets() == [
        "Gemini (노트북 GPU 없음 → 폴백)",
        "집컴 CPU · exaone3.5:2.4b (예비)",
        "Gemini (lora-server 없음 → 폴백)",
    ]


def test_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTFOLIO_LLM_BACKEND", "gemini")
    monkeypatch.setenv("MOVA_CHAT_AGENT", "1")
    monkeypatch.setenv("RECOMMENDATION_BACKEND", "gemini")
    assert _targets() == ["Gemini", "노트북 GPU · mova-agent-v9", "Gemini"]


def test_orchestrator_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOVA_ORCHESTRATOR_ENABLED", "0")
    assert _targets()[1] == "꺼짐 (규칙 기반)"
