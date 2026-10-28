"""어드민 "운영 제어" — 관리자만, 에이전트에 정해진 경로만 전달, 거절 사유·상태 코드 그대로, 못 닿으면 reachable=false."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from shared.security.require_admin import AdminPrincipal, require_admin  # noqa: E402

from viewer.adapter.inbound.api.v1 import admin_ops_router as mod  # noqa: E402
from viewer.adapter.inbound.api.v1.admin_ops_router import admin_ops_router  # noqa: E402

Call = tuple[str, str, dict[str, Any] | None]


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_AGENT_TOKEN", "t")
    monkeypatch.setenv("OPS_AGENT_URL", "http://agent:8210")


def _client(*, admin: bool) -> TestClient:
    app = FastAPI()
    app.include_router(admin_ops_router)
    if admin:
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="a")
    return TestClient(app)


def _fake_agent(
    monkeypatch: pytest.MonkeyPatch, *, result: dict[str, Any] | None = None, error: int = 0
) -> list[Call]:
    calls: list[Call] = []

    async def fake(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append((method, path, body))
        if error:
            raise HTTPException(status_code=error, detail=f"agent {error}")
        return result or {"ok": True}

    monkeypatch.setattr(mod, "_agent", fake)
    return calls


def test_requires_admin() -> None:
    c = _client(admin=False)
    assert c.get("/admin/ops").status_code == 401
    assert c.post("/admin/ops/arda/start").status_code == 401


def test_status_passes_through_and_marks_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_agent(monkeypatch, result={"arda": {"ai_mode": "gpu"}, "gpu": [], "ollama": {}})
    res = _client(admin=True).get("/admin/ops")
    assert res.status_code == 200
    assert res.json()["reachable"] is True
    assert res.json()["arda"]["ai_mode"] == "gpu"


def test_status_unreachable_is_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_agent(monkeypatch, error=503)
    res = _client(admin=True).get("/admin/ops")
    assert res.status_code == 200
    assert res.json()["reachable"] is False


@pytest.mark.parametrize(
    ("url", "body", "expected"),
    [
        ("/admin/ops/arda/start", None, ("POST", "/arda/start", None)),
        ("/admin/ops/arda/stop", None, ("POST", "/arda/stop", None)),
        ("/admin/ops/arda/ai-mode", {"mode": "gpu"}, ("POST", "/arda/ai-mode", {"mode": "gpu"})),
        (
            "/admin/ops/ollama/load",
            {"model": "exaone3.5:7.8b"},
            ("POST", "/ollama/load", {"model": "exaone3.5:7.8b"}),
        ),
        (
            "/admin/ops/ollama/unload",
            {"model": "bge-m3:latest"},
            ("POST", "/ollama/unload", {"model": "bge-m3:latest"}),
        ),
    ],
)
def test_actions_forward_fixed_paths(
    monkeypatch: pytest.MonkeyPatch, url: str, body: dict[str, Any] | None, expected: Call
) -> None:
    calls = _fake_agent(monkeypatch)
    res = _client(admin=True).post(url, json=body) if body else _client(admin=True).post(url)
    assert res.status_code == 200
    assert calls == [expected]


@pytest.mark.parametrize(
    ("url", "body"),
    [
        ("/admin/ops/arda/restart", None),  # 없는 동작
        ("/admin/ops/arda/ai-mode", {"mode": "tpu"}),
        ("/admin/ops/ollama/delete", {"model": "x"}),
        ("/admin/ops/ollama/load", {"model": ""}),
    ],
)
def test_rejects_unknown_actions_before_calling_agent(
    monkeypatch: pytest.MonkeyPatch, url: str, body: dict[str, Any] | None
) -> None:
    calls = _fake_agent(monkeypatch)
    res = _client(admin=True).post(url, json=body) if body else _client(admin=True).post(url)
    assert res.status_code == 422
    assert calls == []


def test_agent_refusal_keeps_status_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_agent(monkeypatch, error=409)
    res = _client(admin=True).post("/admin/ops/arda/start")
    assert res.status_code == 409
    assert res.json()["detail"] == "agent 409"


def test_missing_token_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPS_AGENT_TOKEN")
    res = _client(admin=True).post("/admin/ops/arda/start")
    assert res.status_code == 503
