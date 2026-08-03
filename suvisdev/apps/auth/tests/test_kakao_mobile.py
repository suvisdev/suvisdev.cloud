from __future__ import annotations

import sys
from pathlib import Path

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from auth import mobile_refresh_store as mobile_refresh_module
from auth import refresh_store as refresh_module
from auth.kakao_mobile_verifier import KakaoMobileIdentity, KakaoTokenInvalid
from auth.mobile_refresh_store import MobileRefreshTokenStore
from auth.rbac import Role
from auth.refresh_store import RefreshTokenStore
from auth.repository import User
from auth.security import JwtAdapter
from auth.services import AuthService


class _FakeRedis:
    """dict 기반 최소 Redis 대체 — RefreshTokenStore/MobileRefreshTokenStore가 같은
    인스턴스를 공유하게 해서(client fixture) 모바일/웹 키 네임스페이스가 실제로
    서로 침범하지 않는지 검증할 수 있게 한다."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def set(self, key, value, ex=None):
        self._store[key] = value

    def get(self, key):
        return self._store.get(key)

    def delete(self, key):
        self._store.pop(key, None)


class _FakeKakaoMobileVerifier:
    async def verify(self, access_token: str) -> KakaoMobileIdentity:
        if access_token == "valid-token":
            return KakaoMobileIdentity(provider_user_id="kakao-1", email="a@b.com", nickname="철수")
        raise KakaoTokenInvalid("무효 토큰")


class _FakeUserRepository:
    """모바일(kakao-1)과 웹(shared-user) 로그인이 같은 user_id(42)로 귀결되는 상황을
    재현 — G3(모바일·웹 동시 로그인, 상호 무영향)를 검증하기 위함."""

    async def find_by_credentials(self, username, password):
        if username == "shared-user" and password == "correct-password":
            return User(user_id=42, username="shared-user", roles=[Role.USER])
        return None

    async def find_by_oauth_identity(self, provider, provider_user_id):
        return None

    async def create_user(self, *, email, password, username):
        raise NotImplementedError

    async def find_or_create_by_kakao(self, *, provider_user_id, email, nickname):
        assert provider_user_id == "kakao-1"
        return User(user_id=42, username=nickname or "kakao-user", roles=[Role.USER])


@pytest.fixture()
def shared_fake_redis() -> _FakeRedis:
    return _FakeRedis()


@pytest.fixture()
def client(rsa_keypair, monkeypatch, shared_fake_redis):
    monkeypatch.setattr(mobile_refresh_module.redis, "from_url", lambda *a, **k: shared_fake_redis)
    monkeypatch.setattr(refresh_module.redis, "from_url", lambda *a, **k: shared_fake_redis)

    service = AuthService(
        user_repository=_FakeUserRepository(),
        token_issuer=JwtAdapter(),
        refresh_store=RefreshTokenStore(),
        mobile_refresh_store=MobileRefreshTokenStore(),
        kakao_mobile_verifier=_FakeKakaoMobileVerifier(),
    )

    import auth_main
    from auth import router as auth_router_module

    monkeypatch.setattr(auth_router_module, "_service", service)
    return TestClient(auth_main.app)


# G2 — 유효/무효 access_token ------------------------------------------------


def test_kakao_mobile_login_valid_token_issues_tokens_and_nickname(client):
    resp = client.post("/auth/kakao/mobile", json={"access_token": "valid-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["nickname"] == "철수"


def test_kakao_mobile_login_invalid_token_returns_401(client):
    resp = client.post("/auth/kakao/mobile", json={"access_token": "bad-token"})
    assert resp.status_code == 401


def test_kakao_mobile_login_second_login_resolves_same_user(client):
    first = client.post("/auth/kakao/mobile", json={"access_token": "valid-token"})
    second = client.post("/auth/kakao/mobile", json={"access_token": "valid-token"})
    sub1 = pyjwt.decode(first.json()["access_token"], options={"verify_signature": False})["sub"]
    sub2 = pyjwt.decode(second.json()["access_token"], options={"verify_signature": False})["sub"]
    assert sub1 == sub2 == "42"


def test_mobile_refresh_rotates_and_reuse_is_rejected(client):
    login_resp = client.post("/auth/kakao/mobile", json={"access_token": "valid-token"})
    refresh_token = login_resp.json()["refresh_token"]

    refreshed = client.post("/auth/mobile/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    new_refresh_token = refreshed.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    reuse = client.post("/auth/mobile/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401


# G3 — 모바일/웹 분리 ---------------------------------------------------------


def test_mobile_and_web_sessions_use_isolated_redis_namespaces(client, shared_fake_redis):
    """같은 userId(42)로 모바일·웹 각각 로그인 → 서로 다른 Redis 키 존재 →
    모바일 로그아웃 시 모바일 key만 삭제되고 웹 key는 유지된다."""
    mobile_login = client.post("/auth/kakao/mobile", json={"access_token": "valid-token"})
    mobile_refresh_token = mobile_login.json()["refresh_token"]
    mobile_key = "auth:refresh:mobile:42"
    assert mobile_key in shared_fake_redis._store

    web_login = client.post(
        "/auth/login",
        json={"username": "shared-user", "password": "correct-password", "aud": "suvis-mova"},
    )
    web_refresh_token = web_login.json()["refresh_token"]
    web_key = f"auth:refresh:{web_refresh_token}"
    assert web_key in shared_fake_redis._store
    assert web_key != mobile_key

    logout_resp = client.post("/auth/mobile/logout", json={"refresh_token": mobile_refresh_token})
    assert logout_resp.status_code == 204

    assert mobile_key not in shared_fake_redis._store  # 모바일 세션만 폐기
    assert web_key in shared_fake_redis._store  # 웹 세션은 무영향

    # 웹 refresh는 여전히 정상 동작(모바일 로그아웃에 회귀 없음)
    web_refreshed = client.post("/auth/refresh", json={"refresh_token": web_refresh_token})
    assert web_refreshed.status_code == 200


def test_mobile_logout_then_refresh_fails(client):
    login_resp = client.post("/auth/kakao/mobile", json={"access_token": "valid-token"})
    refresh_token = login_resp.json()["refresh_token"]

    client.post("/auth/mobile/logout", json={"refresh_token": refresh_token})

    refreshed = client.post("/auth/mobile/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 401
