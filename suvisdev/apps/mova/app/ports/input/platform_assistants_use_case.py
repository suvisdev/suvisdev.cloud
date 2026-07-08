"""어시스턴트 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.platform_assistants_dto import AssistantDto, AssistantListDto


class AssistantsUseCase(ABC):
    @abstractmethod
    async def list_assistants(self) -> AssistantListDto:
        pass

    @abstractmethod
    async def get_assistant(self, slug: str) -> AssistantDto | None:
        pass
