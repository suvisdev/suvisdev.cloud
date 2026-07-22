from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from auth import oauth_handoff_store as oauth_handoff_module
from auth import oauth_state_store as oauth_state_module
from auth import refresh_store as refresh_module
from auth.oauth_adapters import OAuthError, OAuthIdentity
from auth.oauth_handoff_store import OAuthHandoffStore
from auth.oauth_state_store import OAuthStateStore
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
    fake_redis = _FakeRedis()
    monkeypatch.setattr(refresh_module.redis, "from_url", lambda *a, **k: fake_redis)
    monkeypatch.setattr(oauth_state_module.redis, "from_url", lambda *a, **k: fake_redis)
    monkeypatch.setattr(oauth_handoff_module.redis, "from_url", lambda *a, **k: fake_redis)

    service = AuthService(
        user_repository=_FakeUserRepository(),
        token_issuer=JwtAdapter(),
        refresh_store=RefreshTokenStore(),
        oauth_adapters={"google": _FakeGoogleAdapter()},
        oauth_state_store=OAuthStateStore(),
        oauth_handoff_store=OAuthHandoffStore(),
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


def _start_login_and_extract_state(
    client, provider: str = "google", aud: str = "suvis-mova", return_to: str | None = None
) -> str:
    params = {"aud": aud}
    if return_to is not None:
        params["return_to"] = return_to
    resp = client.get(f"/auth/login/{provider}", params=params, follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]
    return state


def test_start_oauth_login_redirects_to_provider_authorize_url(client):
    resp = client.get("/auth/login/google", params={"aud": "suvis-mova"}, follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://example.com/authorize?state=")


def test_start_oauth_login_unknown_provider_returns_404(client):
    resp = client.get("/auth/login/facebook", params={"aud": "suvis-mova"}, follow_redirects=False)
    assert resp.status_code == 404


def test_start_oauth_login_without_aud_returns_422(client):
    """aud는 로그인 시작 시점에 프론트가 반드시 알려줘야 함 — 기본값 없이 강제."""
    resp = client.get("/auth/login/google", follow_redirects=False)
    assert resp.status_code == 422


def _callback_and_extract_handoff_code(
    client, *, code: str, state: str, expected_path: str = "/test-auth-login/result"
) -> str:
    resp = client.get(
        "/auth/callback/google", params={"code": code, "state": state}, follow_redirects=False
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert expected_path in location
    return parse_qs(urlparse(location).query)["code"][0]


def test_oauth_callback_linked_identity_redirects_with_handoff_code(client):
    state = _start_login_and_extract_state(client, aud="suvis-mova")
    handoff_code = _callback_and_extract_handoff_code(client, code="valid-code", state=state)
    assert handoff_code


def test_oauth_callback_unlinked_identity_returns_409(client):
    state = _start_login_and_extract_state(client)
    resp = client.get(
        "/auth/callback/google",
        params={"code": "unlinked-code", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 409


def test_oauth_callback_missing_state_returns_400(client):
    resp = client.get("/auth/callback/google", params={"code": "valid-code"}, follow_redirects=False)
    assert resp.status_code == 400


def test_oauth_callback_wrong_state_returns_400(client):
    _start_login_and_extract_state(client)  # 정상 state 하나 발급해두되 사용하지 않음
    resp = client.get(
        "/auth/callback/google",
        params={"code": "valid-code", "state": "not-the-real-state"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_oauth_callback_reused_state_returns_400(client):
    """state는 1회 소비 — 콜백 성공 후 같은 state로 다시 호출하면 거부."""
    state = _start_login_and_extract_state(client)
    _callback_and_extract_handoff_code(client, code="valid-code", state=state)

    second = client.get(
        "/auth/callback/google", params={"code": "valid-code", "state": state}, follow_redirects=False
    )
    assert second.status_code == 400


def test_oauth_callback_uses_aud_saved_at_login_start(client):
    """콜백이 쿼리로 aud를 받는 게 아니라, 로그인 시작 시점에 state에 저장해둔
    aud를 그대로 써서 토큰을 발급하는지 확인(실서비스 버그 회귀 방지)."""
    state = _start_login_and_extract_state(client, aud="suvis-gildle")
    handoff_code = _callback_and_extract_handoff_code(client, code="valid-code", state=state)

    exchanged = client.post("/auth/exchange", json={"code": handoff_code})
    assert exchanged.status_code == 200

    import jwt as pyjwt

    claims = pyjwt.decode(
        exchanged.json()["access_token"], options={"verify_signature": False}
    )
    assert claims["aud"] == "suvis-gildle"


def test_exchange_valid_handoff_code_returns_tokens_once(client):
    state = _start_login_and_extract_state(client)
    handoff_code = _callback_and_extract_handoff_code(client, code="valid-code", state=state)

    first = client.post("/auth/exchange", json={"code": handoff_code})
    assert first.status_code == 200
    assert first.json()["access_token"]

    # 1회 소비 — 같은 code 재사용 불가
    second = client.post("/auth/exchange", json={"code": handoff_code})
    assert second.status_code == 404


def test_exchange_unknown_code_returns_404(client):
    resp = client.post("/auth/exchange", json={"code": "never-issued"})
    assert resp.status_code == 404


def test_oauth_callback_redirects_to_whitelisted_return_to(client):
    state = _start_login_and_extract_state(client, return_to="/mova")
    _callback_and_extract_handoff_code(client, code="valid-code", state=state, expected_path="/mova?code=")


def test_oauth_callback_falls_back_silently_for_non_whitelisted_return_to(client):
    """화이트리스트에 없는 경로는 에러 없이 조용히 기본값으로 폴백한다."""
    state = _start_login_and_extract_state(client, return_to="/not-an-allowed-path")
    _callback_and_extract_handoff_code(client, code="valid-code", state=state)


def test_oauth_callback_falls_back_silently_for_protocol_relative_return_to(client):
    """//evil.com 같은 프로토콜 상대경로(오픈 리다이렉트 시도)는 조용히 기본값으로 폴백한다."""
    state = _start_login_and_extract_state(client, return_to="//evil.com")
    _callback_and_extract_handoff_code(client, code="valid-code", state=state)


class TestSanitizeReturnTo:
    """auth.router._sanitize_return_to 화이트리스트 검증 단위 테스트."""

    @staticmethod
    def _sanitize(value):
        from auth.router import _sanitize_return_to

        return _sanitize_return_to(value)

    def test_none_falls_back_to_default(self):
        assert self._sanitize(None) == "/test-auth-login/result"

    def test_exact_prefix_match_allowed(self):
        assert self._sanitize("/mova") == "/mova"

    def test_subpath_of_allowed_prefix_allowed(self):
        assert self._sanitize("/mova/main") == "/mova/main"

    def test_prefix_collision_rejected(self):
        """/movaXYZ는 /mova로 시작하지만 다른 경로다 — 화이트리스트 우회 방지."""
        assert self._sanitize("/movaXYZ") == "/test-auth-login/result"

    def test_protocol_relative_rejected(self):
        assert self._sanitize("//evil.com") == "/test-auth-login/result"

    def test_absolute_url_rejected(self):
        assert self._sanitize("https://evil.com") == "/test-auth-login/result"

    def test_non_whitelisted_absolute_path_rejected(self):
        assert self._sanitize("/some-other-page") == "/test-auth-login/result"
