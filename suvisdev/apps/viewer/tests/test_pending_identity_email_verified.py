"""약관 동의 대기 신원 저장·복원 시 email_verified 보존(2026-10-20 리뷰).

빠뜨리면 복원값이 기본 False가 되어 검증된 구글 이메일도 기존 계정 연결이
생략되고(중복 계정) ADMIN_EMAILS 관리자도 일반 사용자로 발급됐다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from viewer.adapter.outbound.cache import redis_pending_identity_repository as module  # noqa: E402
from viewer.app.dtos.oauth_dto import OAuthIdentity  # noqa: E402


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


class PendingIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = _FakeRedis()
        p = patch.object(module.redis, "from_url", return_value=self.fake)
        p.start()
        self.addCleanup(p.stop)
        self.repo = module.RedisPendingIdentityRepository()

    def test_email_verified_round_trips(self) -> None:
        for verified in (True, False):
            identity = OAuthIdentity(
                provider="google",
                provider_user_id="g-1",
                email="a@b.com",
                name="A",
                email_verified=verified,
            )
            code = self.repo.save_pending(identity)
            self.assertEqual(self.repo.pop_pending(code=code), identity)

    def test_legacy_payload_without_field_restores_as_unverified(self) -> None:
        self.fake.set(
            "viewer:oauth_pending:old",
            '{"provider": "google", "provider_user_id": "g-1", "email": "a@b.com", "name": "A"}',
        )
        restored = self.repo.pop_pending(code="old")
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertFalse(restored.email_verified)


if __name__ == "__main__":
    unittest.main()
