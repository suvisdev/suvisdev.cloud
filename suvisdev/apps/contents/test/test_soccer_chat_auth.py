"""soccer 챗 require_admin 가드 — 무인증 401, 관리자 통과."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.security.require_admin import AdminPrincipal, require_admin

from contents.adapter.inbound.api.v1.soccer_chat_router import soccer_chat_router
from contents.app.dtos.soccer_chat_dto import SoccerChatDto
from contents.dependencies.soccer_chat_provider import get_soccer_chat_use_case

_BODY = {"messages": [{"role": "user", "content": "안녕"}]}


class _FakeChat:
    def chat(self, messages, system=None) -> SoccerChatDto:
        return SoccerChatDto(reply="ok")


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(soccer_chat_router)
    app.dependency_overrides[get_soccer_chat_use_case] = lambda: _FakeChat()
    return app


def test_chat_without_token_returns_401():
    res = TestClient(_app()).post("/soccer/chat", json=_BODY)
    assert res.status_code == 401


def test_chat_with_admin_passes_gate():
    app = _app()
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="admin-1")
    res = TestClient(app).post("/soccer/chat", json=_BODY)
    assert res.status_code == 200
    assert res.json()["reply"] == "ok"
