from __future__ import annotations

from dataclasses import replace

from fastapi import HTTPException

from gildle.app.dtos.walk_dto import (
    WalkCreateCommand,
    WalkListQuery,
    WalkStats,
    WalkSummary,
)
from gildle.app.ports.input.walk_use_case import WalkUseCase
from gildle.app.ports.output.walk_repository import WalkRepositoryPort
from gildle.domain.entities.walk_entity import Walk

_MAX_PATH_POINTS = 5000  # 1초 간격 기록이면 약 80분치. 그 이상은 잘라 저장한다.


class WalkInteractor(WalkUseCase):
    def __init__(self, repository: WalkRepositoryPort) -> None:
        self._repository = repository

    async def record(self, command: WalkCreateCommand) -> Walk:
        try:
            walk = command.to_domain()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if len(walk.path) > _MAX_PATH_POINTS:
            # 통째로 거부하기보다 앞부분을 남긴다 — 기록 자체를 잃는 편이 더 나쁘다.
            # slots=True dataclass라 __dict__가 없다 — replace로 갈아낀다
            walk = replace(walk, path=walk.path[:_MAX_PATH_POINTS])
        return await self._repository.save(walk)

    async def list_mine(self, query: WalkListQuery) -> list[WalkSummary]:
        return await self._repository.list_by_user(query)

    async def detail(self, walk_id: int, user_id: int) -> Walk:
        walk = await self._repository.get(walk_id)
        # 남의 기록은 "권한 없음"이 아니라 404로 막는다 — 403을 주면 그 id가
        # 존재한다는 사실이 새어 나간다(2026-08-07 mova IDOR 수정과 같은 기준).
        if walk is None or walk.user_id != user_id:
            raise HTTPException(status_code=404, detail="산책 기록을 찾을 수 없습니다.")
        return walk

    async def remove(self, walk_id: int, user_id: int) -> None:
        await self.detail(walk_id, user_id)  # 소유권 확인 후 삭제
        await self._repository.delete(walk_id)

    async def stats(self, user_id: int) -> WalkStats:
        return await self._repository.stats(user_id)
