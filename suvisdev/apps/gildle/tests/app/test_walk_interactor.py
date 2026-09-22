"""산책 기록 유스케이스 — 소유권 검사와 경로 길이 상한 (2026-09-22)."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from gildle.app.dtos.walk_dto import WalkCreateCommand, WalkListQuery, WalkStats, WalkSummary
from gildle.app.ports.output.walk_repository import WalkRepositoryPort
from gildle.app.use_cases.walk_interactor import WalkInteractor
from gildle.domain.entities.walk_entity import Walk

_START = datetime(2026, 9, 22, 9, 0, 0)
_END = _START + timedelta(minutes=30)


class _FakeWalkRepository(WalkRepositoryPort):
    """포트를 실제로 상속한다 — 인터페이스가 바뀌면 테스트가 먼저 깨지게."""

    def __init__(self, stored: list[Walk] | None = None) -> None:
        self.stored = stored or []
        self.deleted: list[int] = []

    async def save(self, walk: Walk) -> Walk:
        saved = replace(walk, id=1)
        self.stored.append(saved)
        return saved

    async def list_by_user(self, query: WalkListQuery) -> list[WalkSummary]:
        return [
            WalkSummary(
                id=w.id or 0,
                started_at=w.started_at,
                ended_at=w.ended_at,
                distance_m=w.distance_m,
                duration_s=w.duration_s,
                season_mode=w.season_mode,
                avg_shade_score=w.avg_shade_score,
            )
            for w in self.stored
            if w.user_id == query.user_id
        ]

    async def get(self, walk_id: int) -> Walk | None:
        return next((w for w in self.stored if w.id == walk_id), None)

    async def delete(self, walk_id: int) -> None:
        self.deleted.append(walk_id)

    async def stats(self, user_id: int) -> WalkStats:
        mine = [w for w in self.stored if w.user_id == user_id]
        return WalkStats(
            total_count=len(mine),
            total_distance_m=sum(w.distance_m for w in mine),
            total_duration_s=sum(w.duration_s for w in mine),
        )


def _command(**over) -> WalkCreateCommand:
    base = dict(
        user_id=7,
        started_at=_START,
        ended_at=_END,
        distance_m=2400,
        duration_s=1800,
        path=[[37.5, 127.0], [37.51, 127.01]],
        season_mode="summer",
    )
    return WalkCreateCommand(**{**base, **over})


class TestRecord:
    @pytest.mark.asyncio
    async def test_saves_with_principal_user(self):
        repo = _FakeWalkRepository()
        walk = await WalkInteractor(repository=repo).record(_command())
        assert walk.id == 1
        assert walk.user_id == 7

    @pytest.mark.asyncio
    async def test_rejects_end_before_start(self):
        repo = _FakeWalkRepository()
        with pytest.raises(HTTPException) as e:
            await WalkInteractor(repository=repo).record(
                _command(started_at=_END, ended_at=_START)
            )
        assert e.value.status_code == 400

    @pytest.mark.asyncio
    async def test_truncates_over_long_path(self):
        """상한 초과 경로는 거부가 아니라 절단 — 기록을 통째로 잃는 편이 더 나쁘다."""
        repo = _FakeWalkRepository()
        walk = await WalkInteractor(repository=repo).record(
            _command(path=[[37.5, 127.0]] * 6000)
        )
        assert len(walk.path) == 5000


class TestOwnership:
    @pytest.mark.asyncio
    async def test_detail_of_other_user_is_404_not_403(self):
        """403을 주면 그 id가 존재한다는 사실이 새어 나간다."""
        mine = Walk(
            id=1, user_id=99, started_at=_START, ended_at=_END,
            distance_m=100, duration_s=60, path=[], season_mode="summer",
        )
        repo = _FakeWalkRepository([mine])
        with pytest.raises(HTTPException) as e:
            await WalkInteractor(repository=repo).detail(1, user_id=7)
        assert e.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_requires_ownership(self):
        other = Walk(
            id=1, user_id=99, started_at=_START, ended_at=_END,
            distance_m=100, duration_s=60, path=[], season_mode="summer",
        )
        repo = _FakeWalkRepository([other])
        with pytest.raises(HTTPException):
            await WalkInteractor(repository=repo).remove(1, user_id=7)
        assert repo.deleted == []  # 소유자가 아니면 삭제까지 가지 않는다
