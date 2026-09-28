"""길들 앱 이메일 회원가입·로그인·회원 탈퇴(2026-09-28, 필수 항목만)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from auth import mobile_refresh_store as mobile_refresh_module
from auth import refresh_store as refresh_module
from auth.mobile_refresh_store import MobileRefreshTokenStore
from auth.rbac import Role
from auth.refresh_store import RefreshTokenStore
from auth.repository import EmailAlreadyExists, User
from auth.security import JwtAdapter
from auth.services import AuthService
from auth.tests.test_kakao_mobile import _FakeKakaoMobileVerifier, _FakeRedis


class _EmailRepo:
    def __init__(self) -> None:
        self.users: dict[str, tuple[int, str]] = {}  # email → (id, password)
        self.deleted: list[int] = []

    async def create_email_user(self, *, email, password):
        if email in self.users:
            raise EmailAlreadyExists("이미 가입된 이메일입니다.")
        self.users[email] = (len(self.users) + 100, password)
        return User(user_id=self.users[email][0], username=email, roles=[Role.USER])

    async def find_by_email_credentials(self, email, password):
        row = self.users.get(email)
        if row is None or row[1] != password:
            return None
        return User(user_id=row[0], username=email, roles=[Role.USER])

    async def delete_user(self, user_id):
        self.deleted.append(user_id)
        before = len(self.users)
        self.users = {k: v for k, v in self.users.items() if v[0] != user_id}
        return len(self.users) < before


@pytest.fixture()
def ctx(rsa_keypair, monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(mobile_refresh_module.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(refresh_module.redis, "from_url", lambda *a, **k: fake)
    repo = _EmailRepo()
    service = AuthService(
        user_repository=repo,  # type: ignore[arg-type]
        token_issuer=JwtAdapter(),
        refresh_store=RefreshTokenStore(),
        mobile_refresh_store=MobileRefreshTokenStore(),
        kakao_mobile_verifier=_FakeKakaoMobileVerifier(),
    )
    import auth_main

    from auth import router as auth_router_module

    monkeypatch.setattr(auth_router_module, "_service", service)
    return TestClient(auth_main.app), repo, fake


def test_signup_needs_only_email_and_password_and_logs_in(ctx):
    client, repo, _ = ctx
    resp = client.post(
        "/auth/mobile/signup", json={"email": " Walker@Example.com ", "password": "longenough"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"] and body["nickname"] == "walker"
    assert "walker@example.com" in repo.users  # 공백·대소문자 정규화
    dup = client.post(
        "/auth/mobile/signup", json={"email": "walker@example.com", "password": "longenough"}
    )
    assert dup.status_code == 409


def test_signup_rejects_short_password_and_bad_email(ctx):
    client, _, _ = ctx
    assert (
        client.post(
            "/auth/mobile/signup", json={"email": "a@b.co", "password": "short"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/mobile/signup", json={"email": "not-email", "password": "longenough"}
        ).status_code
        == 422
    )


def test_email_login(ctx):
    client, _, _ = ctx
    client.post("/auth/mobile/signup", json={"email": "a@b.co", "password": "longenough"})
    ok = client.post("/auth/mobile/login", json={"email": "a@b.co", "password": "longenough"})
    assert ok.status_code == 200 and ok.json()["refresh_token"]
    bad = client.post("/auth/mobile/login", json={"email": "a@b.co", "password": "wrongpass1"})
    assert bad.status_code == 401


def test_delete_account_removes_user_and_mobile_session(ctx):
    client, repo, fake = ctx
    tokens = client.post(
        "/auth/mobile/signup", json={"email": "a@b.co", "password": "longenough"}
    ).json()
    assert client.delete("/auth/mobile/account").status_code == 401
    resp = client.delete(
        "/auth/mobile/account", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 204
    assert repo.deleted == [100] and "a@b.co" not in repo.users
    refreshed = client.post("/auth/mobile/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 401  # 세션도 폐기


def test_delete_account_rejects_web_token(ctx):
    client, _, _ = ctx
    web = JwtAdapter().issue_access_token(sub="100", roles=["user"], aud="suvis-mova")
    resp = client.delete("/auth/mobile/account", headers={"Authorization": f"Bearer {web}"})
    assert resp.status_code == 401
