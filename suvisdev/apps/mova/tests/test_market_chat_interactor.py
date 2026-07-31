from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest  # noqa: E402
from mova.app.use_cases.market_chat_interactor import (  # noqa: E402
    ChatInteractor,
    _GENERAL_CHAT_SYSTEM_PROMPT,
)
from ontology.app.dtos.mycroft_dto import MycroftAnswerDto  # noqa: E402


def _build_interactor(*, classifier_destination: str) -> tuple[ChatInteractor, AsyncMock, AsyncMock]:
    repo = AsyncMock()
    repo.save_chat.return_value = 1
    classifier = AsyncMock()
    classifier.classify.return_value = (classifier_destination, [])
    general = AsyncMock()
    general.ask.return_value = MycroftAnswerDto(text="답변입니다.")

    interactor = ChatInteractor(
        repository=repo,
        recommender=AsyncMock(),
        preferences=AsyncMock(),
        hub_rag=AsyncMock(),
        classifier=classifier,
        general=general,
    )
    return interactor, repo, general


class ChatInteractorGeneralRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_destination_calls_mycroft_with_system_prompt(self) -> None:
        interactor, _repo, general = _build_interactor(classifier_destination="general")
        request = MovaChatRequest(message="오늘 기분 어때?", history=[])

        response = await interactor.chat(request)

        general.ask.assert_awaited_once()
        command = general.ask.await_args.args[0]
        self.assertEqual(command.system, _GENERAL_CHAT_SYSTEM_PROMPT)
        self.assertTrue(command.system)
        self.assertEqual(response.reply, "답변입니다.")
        self.assertEqual(response.recommendations, [])

    async def test_crud_destination_also_calls_mycroft_with_system_prompt(self) -> None:
        """ea167b5에서 crud도 general과 동일 처리로 통합된 구조를 유지하는지 확인."""
        interactor, _repo, general = _build_interactor(classifier_destination="crud")
        request = MovaChatRequest(message="이 리뷰 삭제해줘", history=[])

        await interactor.chat(request)

        general.ask.assert_awaited_once()
        command = general.ask.await_args.args[0]
        self.assertEqual(command.system, _GENERAL_CHAT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
