from __future__ import annotations

from gildle.app.ports.input.account_data_use_case import AccountDataUseCase
from gildle.app.ports.output.push_token_repository import PushTokenRepositoryPort
from gildle.app.ports.output.walk_repository import WalkRepositoryPort


class AccountDataInteractor(AccountDataUseCase):
    def __init__(self, walks: WalkRepositoryPort, push_tokens: PushTokenRepositoryPort) -> None:
        self._walks = walks
        self._push_tokens = push_tokens

    async def erase(self, user_id: int) -> dict[str, int]:
        return {
            "walks": await self._walks.delete_all_by_user(user_id),
            "push_tokens": await self._push_tokens.delete_all_by_user(user_id),
        }
