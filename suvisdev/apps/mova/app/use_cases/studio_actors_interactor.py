"""배우 Interactor — ActorsUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.studio_actors_dto import ActorDetailDto
from mova.app.ports.input.studio_actors_use_case import ActorsUseCase
from mova.app.ports.output.studio_actors_repository import ActorsRepositoryPort


class ActorsInteractor(ActorsUseCase):
    def __init__(self, repository: ActorsRepositoryPort) -> None:
        self._repository = repository

    async def get_actor_detail(self, actor_id: int) -> ActorDetailDto | None:
        return await self._repository.get_by_id(actor_id)
