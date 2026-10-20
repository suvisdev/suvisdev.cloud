"""viewer OAuth state — 서명 + Redis 1회 소비(2026-09-11 리뷰) 회귀 고정.

서명만 검증하던 구 버전은 10분 내 같은 state를 무한 재사용할 수 있어 로그인
CSRF에 쓰일 수 있었고, JWT_SECRET 미설정 시 빈 키 HMAC으로 조용히 약화됐다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from viewer.adapter.inbound.api.v1 import oauth_router as module  # noqa: E402
from viewer.app.dtos.oauth_dto import OAuthCallbackResultDto, SessionPayloadDto  # noqa: E402
from viewer.app.ports.input.oauth_login_use_case import OAuthLoginUseCase  # noqa: E402
from viewer.dependencies.oauth_login_provider import get_oauth_login_use_case  # noqa: E402


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


class _FakeOAuthLoginUseCase(OAuthLoginUseCase):
    def build_authorize_url(self, *, provider: str, state: str) -> str:
        return f"https://provider.example/authorize?state={state}"

    async def handle_callback(self, *, provider: str, code: str) -> OAuthCallbackResultDto:
        return OAuthCallbackResultDto(kind="session", code="handoff")

    def redeem(self, *, code: str) -> SessionPayloadDto | None:
        return None

    async def complete_consent(self, *, code: str, agreed: bool) -> SessionPayloadDto | None:
        return None


class OAuthStateBrowserBindingTests(unittest.TestCase):
    """로그인 CSRF(2026-10-20 리뷰) — state는 로그인을 시작한 브라우저의 쿠키와 맞아야 한다."""

    def setUp(self) -> None:
        self.fake = _FakeRedis()
        patches = [
            patch.object(module, "_state_store", return_value=self.fake),
            patch.dict("os.environ", {"JWT_SECRET": "test-secret"}),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])
        app = FastAPI()
        app.include_router(module.oauth_router)
        app.dependency_overrides[get_oauth_login_use_case] = _FakeOAuthLoginUseCase
        self.app = app

    def _start(self, client: TestClient) -> str:
        resp = client.get("/oauth/google/login", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("httponly", resp.headers["set-cookie"].lower())
        return parse_qs(urlparse(resp.headers["location"]).query)["state"][0]

    def test_callback_in_initiating_browser_succeeds(self) -> None:
        client = TestClient(self.app)
        state = self._start(client)
        resp = client.get(
            "/oauth/google/callback",
            params={"code": "c", "state": state},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("type=session", resp.headers["location"])

    def test_callback_from_another_browser_is_rejected(self) -> None:
        attacker = TestClient(self.app)
        state = self._start(attacker)  # 공격자가 시작한 로그인의 state
        victim = TestClient(self.app)  # 쿠키 없는 피해자 브라우저
        resp = victim.get(
            "/oauth/google/callback",
            params={"code": "c", "state": state},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 400)
        # 거부된 시도가 state를 소비하지 않으므로, 피해자 시도와 무관하게 서명 검증은 그대로다
        self.assertTrue(module._verify_state(state))

    def test_callback_with_cookie_of_other_login_is_rejected(self) -> None:
        client = TestClient(self.app)
        self._start(client)  # 이 브라우저의 쿠키는 자기 로그인 nonce
        other_state = module._sign_state()  # 다른 곳에서 발급된 state
        resp = client.get(
            "/oauth/google/callback",
            params={"code": "c", "state": other_state},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
