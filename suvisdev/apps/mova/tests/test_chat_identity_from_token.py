"""`/mova/chat`의 신원은 토큰에서만 온다 — 바디의 user_id는 무시.

2026-08-07 이전엔 임의의 user_id를 바디에 넣으면 그 사람의 과거 대화·선호로
개인화된 답을 받고, 그 사람의 대화·추천 이력에 기록까지 남길 수 있었다.
비로그인 사용(익명)은 그대로 허용해야 하므로 401로 막지 않는다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from shared.security.require_user import UserPrincipal, optional_user  # noqa: E402

from mova.adapter.inbound.api.rate_limit import chat_rate_limit  # noqa: E402
from mova.adapter.inbound.api.v1.market_chat_router import market_chat_router  # noqa: E402
from mova.app.dtos.market_chat_dto import ChatResponseDto  # noqa: E402
from mova.dependencies.market_chat_provider import get_chat_use_case  # noqa: E402


def _client(use_case, *, principal: UserPrincipal | None) -> TestClient:
    app = FastAPI()
    app.include_router(market_chat_router)
    app.dependency_overrides[get_chat_use_case] = lambda: use_case
    app.dependency_overrides[chat_rate_limit] = lambda: None
    app.dependency_overrides[optional_user] = lambda: principal
    return TestClient(app)


def _use_case() -> AsyncMock:
    uc = AsyncMock()
    uc.chat.return_value = ChatResponseDto(
        chat_id=1,
        reply="답변",
        refined_query="",
        keywords=[],
        intent_type="mood",
        search_filters={},
        recommendations=[],
    )
    return uc


class ChatIdentityTests(unittest.TestCase):
    def test_body_user_id_is_ignored_when_logged_in(self) -> None:
        """남의 user_id를 넣어도 토큰 주인으로 처리돼야 한다."""
        uc = _use_case()
        c = _client(uc, principal=UserPrincipal(user_id=7, username="tester"))

        resp = c.post("/chat", json={"message": "액션 영화", "user_id": 1})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(uc.chat.await_args.args[0].user_id, 7)

    def test_body_user_id_is_ignored_when_anonymous(self) -> None:
        """비로그인 사용은 허용하되 남의 신원을 빌릴 수는 없다."""
        uc = _use_case()
        c = _client(uc, principal=None)

        resp = c.post("/chat", json={"message": "액션 영화", "user_id": 1})

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(uc.chat.await_args.args[0].user_id)

    def test_anonymous_chat_still_works(self) -> None:
        uc = _use_case()
        c = _client(uc, principal=None)

        resp = c.post("/chat", json={"message": "액션 영화"})

        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
