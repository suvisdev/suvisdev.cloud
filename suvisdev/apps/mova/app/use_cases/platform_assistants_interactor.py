"""어시스턴트 Interactor — AssistantsUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.platform_assistants_dto import AssistantDto, AssistantListDto
from mova.app.ports.input.platform_assistants_use_case import AssistantsUseCase
from mova.app.ports.output.platform_assistants_repository import AssistantsRepositoryPort


class AssistantsInteractor(AssistantsUseCase):
    def __init__(self, repository: AssistantsRepositoryPort) -> None:
        self._repository = repository

    async def list_assistants(self) -> AssistantListDto:
        return await self._repository.list_active()

    async def get_assistant(self, slug: str) -> AssistantDto | None:
        return await self._repository.get_by_slug(slug)
