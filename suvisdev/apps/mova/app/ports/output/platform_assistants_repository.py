"""어시스턴트 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.platform_assistants_dto import AssistantDto, AssistantListDto


class AssistantsRepositoryPort(ABC):
    @abstractmethod
    async def list_active(self) -> AssistantListDto:
        """is_active=true인 어시스턴트 목록."""

    @abstractmethod
    async def get_by_slug(self, slug: str) -> AssistantDto | None:
        """slug로 어시스턴트 단건 조회."""
