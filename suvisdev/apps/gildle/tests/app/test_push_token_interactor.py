"""FCM 토큰 등록·해제 유스케이스 (2026-09-27)."""

from dataclasses import replace

import pytest

from gildle.app.errors import PushTokenValidationError
from gildle.app.ports.output.push_token_repository import PushTokenRepositoryPort
from gildle.app.use_cases.push_token_interactor import PushTokenInteractor
from gildle.domain.entities.push_token_entity import PushToken


class _FakeRepo(PushTokenRepositoryPort):
    def __init__(self) -> None:
        self.rows: dict[str, PushToken] = {}

    async def upsert(self, token: PushToken) -> PushToken:
        saved = replace(
            token,
            id=len(self.rows) + 1 if token.token not in self.rows else self.rows[token.token].id,
        )
        self.rows[token.token] = saved
        return saved

    async def delete(self, user_id: int, token: str) -> None:
        row = self.rows.get(token)
        if row and row.user_id == user_id:
            del self.rows[token]


@pytest.mark.asyncio
async def test_register_trims_and_upserts_same_token_to_new_user():
    repo = _FakeRepo()
    uc = PushTokenInteractor(repo)
    first = await uc.register(1, "  abc  ", "android")
    second = await uc.register(2, "abc", "android")
    assert first.token == "abc"
    assert second.id == first.id and repo.rows["abc"].user_id == 2


@pytest.mark.asyncio
async def test_register_rejects_bad_platform_and_empty_token():
    uc = PushTokenInteractor(_FakeRepo())
    with pytest.raises(PushTokenValidationError):
        await uc.register(1, "abc", "web")
    with pytest.raises(PushTokenValidationError):
        await uc.register(1, "   ", "android")


@pytest.mark.asyncio
async def test_unregister_only_own_token_and_is_idempotent():
    repo = _FakeRepo()
    uc = PushTokenInteractor(repo)
    await uc.register(1, "abc", "android")
    await uc.unregister(2, "abc")  # 남의 토큰 — 무시
    assert "abc" in repo.rows
    await uc.unregister(1, "abc")
    await uc.unregister(1, "abc")  # 두 번째도 조용히
    assert repo.rows == {}
