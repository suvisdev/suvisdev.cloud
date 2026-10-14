from __future__ import annotations

import time

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from auth import google_mobile_verifier as verifier_module
from auth import mobile_refresh_store as mobile_refresh_module
from auth import refresh_store as refresh_module
from auth.google_mobile_verifier import (
    GoogleMobileIdentity,
    GoogleMobileTokenVerifier,
    GoogleTokenInvalid,
)
from auth.mobile_refresh_store import MobileRefreshTokenStore
from auth.rbac import Role
from auth.refresh_store import RefreshTokenStore
from auth.repository import EmailAlreadyExists, User
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


class _FakeGoogleVerifier:
    async def verify(self, id_token: str) -> GoogleMobileIdentity:
        if id_token == "new-user":
            return GoogleMobileIdentity("g-1", "new@gmail.com", "새사람")
        if id_token == "taken-email":
            return GoogleMobileIdentity("g-2", "taken@gmail.com", "중복")
        raise GoogleTokenInvalid("무효 토큰")


class _FakeUserRepository:
    async def find_or_create_by_google(self, *, provider_user_id, email, nickname):
        if email == "taken@gmail.com":
            raise EmailAlreadyExists("이미 가입된 이메일입니다.")
        return User(user_id=7, username="new_abc123", roles=[Role.USER])


@pytest.fixture()
def client(rsa_keypair, monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(mobile_refresh_module.redis, "from_url", lambda *a, **k: fake_redis)
    monkeypatch.setattr(refresh_module.redis, "from_url", lambda *a, **k: fake_redis)
    service = AuthService(
        user_repository=_FakeUserRepository(),
        token_issuer=JwtAdapter(),
        refresh_store=RefreshTokenStore(),
        mobile_refresh_store=MobileRefreshTokenStore(),
        google_mobile_verifier=_FakeGoogleVerifier(),
    )

    import auth_main

    from auth import router as auth_router_module

    monkeypatch.setattr(auth_router_module, "_service", service)
    return TestClient(auth_main.app)


def test_google_mobile_login_issues_tokens(client):
    resp = client.post("/auth/google/mobile", json={"id_token": "new-user"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["nickname"] == "새사람"


def test_google_mobile_login_invalid_token_returns_401(client):
    resp = client.post("/auth/google/mobile", json={"id_token": "forged"})
    assert resp.status_code == 401


def test_google_mobile_login_existing_email_returns_409(client):
    # 사용자 결정(2026-10-02): 같은 이메일 계정이 있으면 연결하지 않고 '이미 가입됨'.
    resp = client.post("/auth/google/mobile", json={"id_token": "taken-email"})
    assert resp.status_code == 409


# 검증기 — 서명·aud는 PyJWT가 보고, 여기선 email_verified 처리만 고정한다 ----------------


@pytest.fixture()
def google_key(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _FakeJwkClient:
        def __init__(self, _url: str) -> None:
            pass

        def get_signing_key_from_jwt(self, _token: str):
            return type("K", (), {"key": key.public_key()})()

    monkeypatch.setattr(verifier_module, "PyJWKClient", _FakeJwkClient)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "web-client.apps.googleusercontent.com")
    return key


def _id_token(key, **claims) -> str:
    now = int(time.time())
    payload = {
        "iss": "https://accounts.google.com",
        "aud": "web-client.apps.googleusercontent.com",
        "sub": "g-1",
        "iat": now,
        "exp": now + 600,
        **claims,
    }
    return pyjwt.encode(payload, key, algorithm="RS256")


@pytest.mark.asyncio
async def test_verifier_keeps_verified_email(google_key):
    token = _id_token(google_key, email="a@gmail.com", email_verified=True, name="에이")
    identity = await GoogleMobileTokenVerifier().verify(token)
    assert identity == GoogleMobileIdentity("g-1", "a@gmail.com", "에이")


@pytest.mark.asyncio
async def test_verifier_drops_unverified_email(google_key):
    token = _id_token(google_key, email="a@gmail.com", email_verified=False)
    identity = await GoogleMobileTokenVerifier().verify(token)
    assert identity.email is None


@pytest.mark.asyncio
async def test_verifier_rejects_other_audience(google_key):
    token = _id_token(google_key, aud="someone-else.apps.googleusercontent.com")
    with pytest.raises(GoogleTokenInvalid):
        await GoogleMobileTokenVerifier().verify(token)
