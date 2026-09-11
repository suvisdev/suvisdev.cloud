"""OAuth 세션의 role 산출 이메일은 검증된 것만 — 2026-09-11 리뷰 H1·H2 회귀 고정.

- H2: 네이버처럼 `email_verified=False`인 신원의 이메일을 `issue_session`에
  넘기면, 사용자가 프로바이더 프로필 이메일을 ADMIN_EMAILS 주소로 바꿔
  role=admin 세션을 얻는 경로가 된다. 인터랙터는 미검증이면 email=None을
  넘겨야 한다.
- H1(보조): viewer `_verify_password`는 평문 동등 비교를 허용하지 않는다.
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

import bcrypt  # noqa: E402

from viewer.adapter.outbound.pg.login_pg_repository import _verify_password  # noqa: E402
from viewer.app.dtos.auth_command_dto import LoginResponseDto  # noqa: E402
from viewer.app.dtos.oauth_dto import OAuthIdentity  # noqa: E402
from viewer.app.use_cases.oauth_login_interactor import OAuthLoginInteractor  # noqa: E402


class _FakeSessionStore:
    def __init__(self) -> None:
        self.issued: list[dict] = []

    def issue_session(self, *, user_id, username, nickname, email):
        self.issued.append({"user_id": user_id, "email": email})
        return "handoff-code"

    def redeem_handoff_code(self, *, code):
        return None


class _FakeIdentityRepo:
    def __init__(self, linked: LoginResponseDto | None) -> None:
        self._linked = linked

    async def find_linked_user(self, identity):
        return self._linked

    async def create_linked_user(self, identity):
        raise AssertionError("이 테스트에서 호출되면 안 된다")


class _FakePendingRepo:
    def save_pending(self, identity):
        return "pending-code"

    def pop_pending(self, *, code):
        return None


def _make_interactor(store: _FakeSessionStore, linked: LoginResponseDto):
    return OAuthLoginInteractor(
        providers={"naver": _FakeProvider()},
        identity_repository=_FakeIdentityRepo(linked),
        pending_repository=_FakePendingRepo(),
        session_store=store,
    )


class _FakeProvider:
    def __init__(self) -> None:
        self.identity: OAuthIdentity | None = None

    def build_authorize_url(self, *, state):
        return "https://example.com"

    async def exchange_code(self, *, code):
        assert self.identity is not None
        return self.identity


class VerifiedEmailRoleTests(unittest.IsolatedAsyncioTestCase):
    async def _callback_email(self, *, email_verified: bool):
        store = _FakeSessionStore()
        linked = LoginResponseDto(user_id=7, username="u7", nickname="닉")
        interactor = _make_interactor(store, linked)
        provider = interactor._providers["naver"]
        provider.identity = OAuthIdentity(
            provider="naver",
            provider_user_id="pid",
            email="admin@example.com",
            name="공격자",
            email_verified=email_verified,
        )
        await interactor.handle_callback(provider="naver", code="c")
        return store.issued[0]["email"]

    async def test_unverified_email_not_passed_to_session(self) -> None:
        self.assertIsNone(await self._callback_email(email_verified=False))

    async def test_verified_email_passed_to_session(self) -> None:
        self.assertEqual(await self._callback_email(email_verified=True), "admin@example.com")


class VerifyPasswordTests(unittest.TestCase):
    def test_rejects_raw_equality_and_pass_the_hash(self) -> None:
        digest = hashlib.sha256(b"pw").hexdigest()
        self.assertFalse(_verify_password("plaintext", "plaintext"))
        self.assertFalse(_verify_password(digest, digest))

    def test_accepts_sha256_and_bcrypt(self) -> None:
        digest = hashlib.sha256(b"pw").hexdigest()
        self.assertTrue(_verify_password("pw", digest))
        hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode()
        self.assertTrue(_verify_password("pw", hashed))


if __name__ == "__main__":
    unittest.main()
