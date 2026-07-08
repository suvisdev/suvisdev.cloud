"""배우 Input Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_actors_dto import ActorDetailDto


class ActorsUseCase(ABC):
    @abstractmethod
    async def get_actor_detail(self, actor_id: int) -> ActorDetailDto | None:
        """배우/감독 상세 + filmography. 없으면 None."""
