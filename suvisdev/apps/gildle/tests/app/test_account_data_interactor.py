"""회원 탈퇴 시 gildle 데이터 삭제 — 본인 것만 지운다(2026-09-28)."""

from __future__ import annotations

import pytest
from tests.app.test_push_token_interactor import _FakeRepo
from tests.app.test_walk_interactor import _END, _START, _FakeWalkRepository

from gildle.app.use_cases.account_data_interactor import AccountDataInteractor
from gildle.domain.entities.push_token_entity import PushToken
from gildle.domain.entities.walk_entity import Walk


def _walk(walk_id: int, user_id: int) -> Walk:
    return Walk(
        id=walk_id,
        user_id=user_id,
        started_at=_START,
        ended_at=_END,
        distance_m=100,
        duration_s=60,
        path=[],
        season_mode="summer_shade",
    )


@pytest.mark.asyncio
async def test_erase_removes_only_my_walks_and_tokens():
    walks = _FakeWalkRepository([_walk(1, 7), _walk(2, 7), _walk(3, 99)])
    tokens = _FakeRepo()
    await tokens.upsert(PushToken(id=None, user_id=7, token="a", platform="android"))
    await tokens.upsert(PushToken(id=None, user_id=99, token="b", platform="android"))

    result = await AccountDataInteractor(walks=walks, push_tokens=tokens).erase(7)

    assert result == {"walks": 2, "push_tokens": 1}
    assert [w.user_id for w in walks.stored] == [99]
    assert list(tokens.rows) == ["b"]
