from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.app.dtos.walk_dto import WalkListQuery, WalkStats, WalkSummary
from gildle.domain.entities.walk_entity import Walk


class WalkRepositoryPort(ABC):
    """산책 기록 저장소 출력 포트."""

    @abstractmethod
    async def save(self, walk: Walk) -> Walk:
        """저장하고 id가 채워진 Walk를 돌려준다."""
        ...

    @abstractmethod
    async def list_by_user(self, query: WalkListQuery) -> list[WalkSummary]:
        """최근 순 목록. 경로 좌표는 제외한다."""
        ...

    @abstractmethod
    async def get(self, walk_id: int) -> Walk | None:
        """단건 조회. 소유권 검사는 호출부(유스케이스)가 한다."""
        ...

    @abstractmethod
    async def delete(self, walk_id: int) -> None: ...

    @abstractmethod
    async def stats(self, user_id: int) -> WalkStats:
        """누적 횟수·거리·시간."""
        ...
