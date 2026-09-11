"""viewer OAuth state — 서명 + Redis 1회 소비(2026-09-11 리뷰) 회귀 고정.

서명만 검증하던 구 버전은 10분 내 같은 state를 무한 재사용할 수 있어 로그인
CSRF에 쓰일 수 있었고, JWT_SECRET 미설정 시 빈 키 HMAC으로 조용히 약화됐다.
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

from viewer.adapter.inbound.api.v1 import oauth_router as module  # noqa: E402


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


class OAuthStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = _FakeRedis()
        self._patches = [
            patch.object(module, "_state_store", return_value=self.fake),
            patch.dict("os.environ", {"JWT_SECRET": "test-secret"}),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._patches])

    def test_state_verifies_once_then_rejected(self) -> None:
        state = module._sign_state()
        self.assertTrue(module._verify_state(state))
        self.assertFalse(module._verify_state(state), "재사용된 state는 거부돼야 한다")

    def test_forged_state_rejected(self) -> None:
        state = module._sign_state()
        nonce, ts, _sig = state.split(".")
        self.assertFalse(module._verify_state(f"{nonce}.{ts}.deadbeef"))

    def test_missing_secret_raises(self) -> None:
        with patch.dict("os.environ", {"JWT_SECRET": ""}):
            with self.assertRaises(RuntimeError):
                module._sign_state()


if __name__ == "__main__":
    unittest.main()
