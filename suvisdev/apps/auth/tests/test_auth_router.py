from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from auth import refresh_store as refresh_module
from auth.oauth_adapters import OAuthError, OAuthIdentity
from auth.rbac import Role
from auth.refresh_store import RefreshTokenStore
from auth.repository import User
from auth.security import JwtAdapter
from auth.services import AuthService


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def set(self, key, value, ex=None):
        self._store[key] = value

    def get(self, key):
        return self._store.get(key)

    def delete(self, key):
        self._store.pop(key, None)


class _FakeUserRepository:
    async def find_by_credentials(self, username, password):
        if username == "admin" and password == "correct-password":
            return User(user_id=1, username="admin", roles=[Role.ADMIN])
        return None

    async def find_by_oauth_identity(self, provider, provider_user_id):
        if provider == "google" and provider_user_id == "linked-sub":
            return User(user_id=2, username="linked-user", roles=[Role.USER])
        return None


class _FakeGoogleAdapter:
    def build_authorize_url(self, state):
        return f"https://example.com/authorize?state={state}"

    async def exchange_code(self, code):
        if code == "valid-code":
            return OAuthIdentity(provider="google", provider_user_id="linked-sub", email="a@b.com")
        if code == "unlinked-code":
            return OAuthIdentity(provider="google", provider_user_id="unlinked-sub", email="c@d.com")
        raise OAuthError("잘못된 코드", status_code=400)


@pytest.fixture()
def client(rsa_keypair, monkeypatch):
    monkeypatch.setattr(refresh_module.redis, "from_url", lambda *a, **k: _FakeRedis())

    service = AuthService(
        user_repository=_FakeUserRepository(),
        token_issuer=JwtAdapter(),
        refresh_store=RefreshTokenStore(),
        oauth_adapters={"google": _FakeGoogleAdapter()},
    )

    import auth_main
    from auth import router as auth_router_module

    monkeypatch.setattr(auth_router_module, "_service", service)
    return TestClient(auth_main.app)


def test_login_success_issues_tokens(client):
    resp = client.post(
        "/auth/login", json={"username": "admin", "password": "correct-password", "aud": "suvis-mova"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password_returns_401(client):
    resp = client.post(
        "/auth/login", json={"username": "admin", "password": "wrong", "aud": "suvis-mova"}
    )
    assert resp.status_code == 401


def test_refresh_rotates_and_reuse_is_rejected(client):
    login_resp = client.post(
        "/auth/login", json={"username": "admin", "password": "correct-password", "aud": "suvis-mova"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    refreshed = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    new_refresh_token = refreshed.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    reuse = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401

    # 재사용 감지로 family 전체가 폐기되어, 정상 파생 토큰도 더 이상 못 씀
    also_revoked = client.post("/auth/refresh", json={"refresh_token": new_refresh_token})
    assert also_revoked.status_code == 401


def test_oauth_callback_linked_identity_succeeds(client):
    resp = client.get("/auth/callback/google", params={"code": "valid-code", "aud": "suvis-mova"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_oauth_callback_unlinked_identity_returns_409(client):
    resp = client.get("/auth/callback/google", params={"code": "unlinked-code", "aud": "suvis-mova"})
    assert resp.status_code == 409
