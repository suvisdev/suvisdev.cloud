"""배우 Output Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_actors_dto import ActorDetailDto


class ActorsRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, actor_id: int) -> ActorDetailDto | None:
        """배우/감독 상세 + 출연작 목록 조회. 없으면 None."""
