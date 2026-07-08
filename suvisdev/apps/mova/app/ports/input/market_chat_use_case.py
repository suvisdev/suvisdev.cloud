"""채팅 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest
from mova.app.dtos.market_chat_dto import ChatResponseDto


class ChatUseCase(ABC):
    @abstractmethod
    async def chat(self, request: MovaChatRequest) -> ChatResponseDto:
        pass
