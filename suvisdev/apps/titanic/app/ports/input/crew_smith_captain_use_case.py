from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.adapter.inbound.api.schemas.crew_smith_captain_schema import (
    ChatSchema,
    SmithCaptainSchema,
)
from titanic.app.dtos.crew_smith_captain_dto import SmithCaptainResponse, SmithChatResponse


class SmithCaptainUseCase(ABC):
    """smith_captain input port."""

    @abstractmethod
    async def chat(self, schema: ChatSchema) -> SmithChatResponse:
        pass


    @abstractmethod
    async def introduce_myself(self, schemas: SmithCaptainSchema, 
) -> SmithCaptainResponse:
        pass

