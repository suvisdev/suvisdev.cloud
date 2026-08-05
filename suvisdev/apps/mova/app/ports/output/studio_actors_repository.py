"""배우 Output Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_actors_dto import ActorDetailDto, ActorUpsertCommand


class ActorsRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, actor_id: int) -> ActorDetailDto | None:
        """배우/감독 상세 + 출연작 목록 조회. 없으면 None."""

    @abstractmethod
    async def upsert_actor(self, command: ActorUpsertCommand) -> int:
        """tmdb_person_id 기준 insert 또는 update — actor.id 반환."""

    @abstractmethod
    async def rollback(self) -> None:
        """같은 세션을 쓰는 다른 upsert(characters/movie_directors)가 실패해
        커밋되지 못한 채 남았을 때, 그 오염을 정리하고 다음 인물 처리로
        넘어가기 위한 세션 롤백. actors 자신의 실패에도 동일하게 쓴다."""
