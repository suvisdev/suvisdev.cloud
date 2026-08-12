from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.dtos.market_conversations_dto import (  # noqa: E402
    ConversationDetailDto,
    ConversationMessageDto,
    ConversationSummaryDto,
)
from mova.app.ports.output.market_conversations_errors import (  # noqa: E402
    ConversationForbiddenError,
    ConversationNotFoundError,
)
from mova.app.use_cases.market_conversations_interactor import (  # noqa: E402
    ConversationsInteractor,
)


class ConversationsInteractorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repo = AsyncMock()
        self.interactor = ConversationsInteractor(repository=self.repo)

    async def test_list_mine_returns_repo_result(self) -> None:
        self.repo.list_by_user.return_value = [
            ConversationSummaryDto(
                id=1, title="영화 추천 얘기", updated_at=datetime.now(UTC), message_count=4
            )
        ]

        result = await self.interactor.list_mine(user_id=42)

        self.repo.list_by_user.assert_awaited_once_with(42)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "영화 추천 얘기")

    async def test_get_mine_raises_not_found_when_missing(self) -> None:
        self.repo.get_owner_id.return_value = None

        with self.assertRaises(ConversationNotFoundError):
            await self.interactor.get_mine(conversation_id=99, user_id=42)

        self.repo.get_detail.assert_not_called()

    async def test_get_mine_raises_forbidden_when_wrong_owner(self) -> None:
        self.repo.get_owner_id.return_value = 7  # 다른 사람 소유

        with self.assertRaises(ConversationForbiddenError):
            await self.interactor.get_mine(conversation_id=99, user_id=42)

    async def test_get_mine_returns_detail_when_owner_matches(self) -> None:
        now = datetime.now(UTC)
        self.repo.get_owner_id.return_value = 42
        self.repo.get_detail.return_value = ConversationDetailDto(
            id=99,
            title="스릴러 얘기",
            created_at=now,
            updated_at=now,
            messages=[
                ConversationMessageDto(
                    id=1, role="user", content="스릴러 추천", meta={}, created_at=now
                ),
                ConversationMessageDto(
                    id=2, role="assistant", content="세븐 어때요?", meta={}, created_at=now
                ),
            ],
        )

        detail = await self.interactor.get_mine(conversation_id=99, user_id=42)

        self.assertEqual(detail.title, "스릴러 얘기")
        self.assertEqual(len(detail.messages), 2)

    async def test_delete_mine_calls_repo_when_owner_matches(self) -> None:
        self.repo.get_owner_id.return_value = 42

        await self.interactor.delete_mine(conversation_id=99, user_id=42)

        self.repo.delete.assert_awaited_once_with(99)

    async def test_delete_mine_forbidden_when_wrong_owner(self) -> None:
        self.repo.get_owner_id.return_value = 7

        with self.assertRaises(ConversationForbiddenError):
            await self.interactor.delete_mine(conversation_id=99, user_id=42)

        self.repo.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
