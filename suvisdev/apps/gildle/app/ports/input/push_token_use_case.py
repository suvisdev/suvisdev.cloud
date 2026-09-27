from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.entities.push_token_entity import PushToken


class PushTokenUseCase(ABC):
    @abstractmethod
    async def register(self, user_id: int, token: str, platform: str) -> PushToken: ...

    @abstractmethod
    async def unregister(self, user_id: int, token: str) -> None: ...
