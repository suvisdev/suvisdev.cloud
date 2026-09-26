"""POST /portfolio/chat 라우터 — 스키마 변환·검증 422·업스트림 오류 일반 문구·IP 레이트리밋 429."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from ontology.adapter.inbound.api.v1.portfolio_chat_router import (  # noqa: E402
    GENERIC_ERROR_DETAIL,
    portfolio_chat_router,
)
from ontology.app.dtos.portfolio_chat_dto import (  # noqa: E402
    PortfolioChatAnswerDto,
    PortfolioChatCommand,
)
from ontology.app.ports.input.portfolio_chat_use_case import PortfolioChatUseCase  # noqa: E402
from ontology.app.ports.output.hub_rag_errors import HubRagError  # noqa: E402
from ontology.dependencies.portfolio_chat_provider import (  # noqa: E402
    get_portfolio_chat_use_case,
)


class _FakeUseCase(PortfolioChatUseCase):
    def __init__(self, *, error: HubRagError | None = None) -> None:
        self.error = error
        self.commands: list[PortfolioChatCommand] = []

    async def chat(self, command: PortfolioChatCommand) -> PortfolioChatAnswerDto:
        self.commands.append(command)
        if self.error:
            raise self.error
        return PortfolioChatAnswerDto(reply="답", sources=("Mova", "Gildle"))


def _client(use_case: PortfolioChatUseCase) -> TestClient:
    app = FastAPI()
    app.include_router(portfolio_chat_router, prefix="/portfolio")
    app.dependency_overrides[get_portfolio_chat_use_case] = lambda: use_case
    return TestClient(app)


class PortfolioChatRouterTests(unittest.TestCase):
    def test_success_shape_and_command_conversion(self) -> None:
        uc = _FakeUseCase()
        res = _client(uc).post(
            "/portfolio/chat",
            json={"message": "  무슨 앱?  ", "history": [{"role": "user", "content": "안녕"}]},
            headers={"cf-connecting-ip": "10.0.0.1"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"reply": "답", "sources": ["Mova", "Gildle"]})
        cmd = uc.commands[0]
        self.assertEqual(cmd.message, "무슨 앱?")
        self.assertEqual(cmd.history[0].role, "user")
        self.assertEqual(cmd.history[0].content, "안녕")

    def test_empty_message_is_422(self) -> None:
        res = _client(_FakeUseCase()).post(
            "/portfolio/chat", json={"message": ""}, headers={"cf-connecting-ip": "10.0.0.2"}
        )
        self.assertEqual(res.status_code, 422)

    def test_history_over_ten_turns_is_422(self) -> None:
        history = [{"role": "user", "content": str(i)} for i in range(11)]
        res = _client(_FakeUseCase()).post(
            "/portfolio/chat",
            json={"message": "q", "history": history},
            headers={"cf-connecting-ip": "10.0.0.3"},
        )
        self.assertEqual(res.status_code, 422)

    def test_upstream_error_maps_status_and_hides_detail(self) -> None:
        raw = "Ollama 호출 실패 (HTTP 500): internal stack trace"
        res = _client(_FakeUseCase(error=HubRagError(raw, status_code=503))).post(
            "/portfolio/chat", json={"message": "q"}, headers={"cf-connecting-ip": "10.0.0.4"}
        )
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["detail"], GENERIC_ERROR_DETAIL)
        self.assertNotIn("stack trace", res.text)

    def test_rate_limit_after_twenty_calls(self) -> None:
        client = _client(_FakeUseCase())
        headers = {"cf-connecting-ip": "10.0.0.5"}
        for _ in range(20):
            self.assertEqual(
                client.post("/portfolio/chat", json={"message": "q"}, headers=headers).status_code,
                200,
            )
        res = client.post("/portfolio/chat", json={"message": "q"}, headers=headers)
        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)


if __name__ == "__main__":
    unittest.main()
