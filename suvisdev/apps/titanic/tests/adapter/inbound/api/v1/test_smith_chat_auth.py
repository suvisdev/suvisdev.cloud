"""smith 챗 require_admin 가드 — 무인증 401, 관리자 통과."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.security.require_admin import AdminPrincipal, require_admin

from titanic.adapter.inbound.api.v1.crew_smith_captain_router import smith_captain_router
from titanic.app.dtos.crew_smith_captain_dto import SmithChatResponse
from titanic.dependencies.crew_smith_captain_provider import get_smith_captain_use_case

_BODY = {"messages": [{"role": "user", "content": "탑승객이 몇 명이야?"}]}


class _FakeSmith:
    async def chat(self, schema) -> SmithChatResponse:
        return SmithChatResponse(reply="ok")


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(smith_captain_router)
    app.dependency_overrides[get_smith_captain_use_case] = lambda: _FakeSmith()
    return app


def test_chat_without_token_returns_401():
    res = TestClient(_app()).post("/smith/chat", json=_BODY)
    assert res.status_code == 401


def test_chat_with_admin_passes_gate():
    app = _app()
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="admin-1")
    res = TestClient(app).post("/smith/chat", json=_BODY)
    assert res.status_code == 200
    assert res.json()["reply"] == "ok"
