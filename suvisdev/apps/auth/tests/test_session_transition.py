"""배포 전환 시나리오(2026-10-20 2차 리뷰) — 형식 표식(sv) 없는 옛 refresh 세션.

배포 전 admins 로그인 세션은 sub가 양수 admins.id라, 그대로 refresh하면 같은 번호의
users 행으로 해석돼 남의 역할로 토큰이 나온다. admin 역할이 든 옛 세션은 거부·폐기하고,
일반 사용자 옛 세션은 그대로 통과시켜 전체 재로그인을 피한다(웹·모바일 공통).
"""

from __future__ import annotations

import json

import pytest

from auth import mobile_refresh_store as mobile_refresh_module
from auth import refresh_store as refresh_module
from auth.mobile_refresh_store import MobileRefreshTokenStore, MobileTokenInvalid
from auth.rbac import Role
from auth.refresh_store import RefreshTokenStore, ReuseDetected
from auth.repository import User
from auth.security import JwtAdapter
from auth.services import AuthService
from auth.tests.test_kakao_mobile import _FakeRedis


class _FakeUserRepository:
    """users.id=1은 일반 사용자 — 옛 admin 세션(sub=1)이 이 계정으로 잘못 풀리면 안 된다."""

    async def find_by_subject(self, sub):
        return User(user_id=int(sub), username="", roles=[Role.USER]) if sub == "1" else None


@pytest.fixture()
def ctx(rsa_keypair, monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(refresh_module.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(mobile_refresh_module.redis, "from_url", lambda *a, **k: fake)
    service = AuthService(
        user_repository=_FakeUserRepository(),  # type: ignore[arg-type]
        token_issuer=JwtAdapter(),
        refresh_store=RefreshTokenStore(),
        mobile_refresh_store=MobileRefreshTokenStore(),
    )
    return service, fake


def _old_web_session(fake: _FakeRedis, jti: str, roles: list[str]) -> None:
    fake.set(
        f"auth:refresh:{jti}",
        json.dumps(
            {"sub": "1", "aud": "suvis-mova", "roles": roles, "family_id": "fam", "used": False}
        ),
    )


def _old_mobile_session(fake: _FakeRedis, roles: list[str]) -> None:
    fake.set(
        "auth:refresh:mobile:1",
        json.dumps({"secret": "s", "sub": "1", "aud": "suvis-susu", "roles": roles}),
    )


@pytest.mark.asyncio
async def test_old_web_admin_session_is_rejected_and_family_revoked(ctx):
    service, fake = ctx
    _old_web_session(fake, "old", ["admin"])
    with pytest.raises(ReuseDetected):
        await service.refresh("old")
    assert fake.get("auth:family:fam:revoked") is not None


@pytest.mark.asyncio
async def test_old_web_user_session_still_refreshes(ctx):
    service, fake = ctx
    _old_web_session(fake, "old", ["user"])
    resp = await service.refresh("old")
    assert resp.refresh_token != "old"
    again = await service.refresh(resp.refresh_token)  # 새 형식으로 이어진다
    assert again.access_token


@pytest.mark.asyncio
async def test_old_mobile_admin_session_is_rejected_and_revoked(ctx):
    service, fake = ctx
    _old_mobile_session(fake, ["admin"])
    with pytest.raises(MobileTokenInvalid):
        await service.mobile_refresh("1:s")
    assert fake.get("auth:refresh:mobile:1") is None


@pytest.mark.asyncio
async def test_old_mobile_user_session_still_refreshes(ctx):
    service, fake = ctx
    _old_mobile_session(fake, ["user"])
    resp = await service.mobile_refresh("1:s")
    assert resp.refresh_token.startswith("1:")
    assert json.loads(fake.get("auth:refresh:mobile:1") or "{}")["sv"] == 2
