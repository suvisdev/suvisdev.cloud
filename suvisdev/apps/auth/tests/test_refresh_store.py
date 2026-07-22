from __future__ import annotations

import pytest

from auth import refresh_store as module
from auth.refresh_store import (
    RefreshTokenStore,
    ReuseDetected,
)


class _FakeRedis:
    """dict 기반 최소 Redis 대체 — get/set/delete만 구현."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.fixture()
def adapter(monkeypatch) -> RefreshTokenStore:
    fake = _FakeRedis()
    monkeypatch.setattr(module.redis, "from_url", lambda *a, **k: fake)
    return RefreshTokenStore()


def test_issue_then_rotate_succeeds(adapter):
    jti, family_id = adapter.issue(sub="42", aud="suvis-mova", roles=["user"])
    rotated = adapter.rotate(jti=jti)
    assert rotated.family_id == family_id
    assert rotated.jti != jti
    assert rotated.sub == "42"
    assert rotated.aud == "suvis-mova"
    assert rotated.roles == ["user"]


def test_reusing_rotated_jti_raises_and_revokes_family(adapter):
    jti, family_id = adapter.issue(sub="42", aud="suvis-mova", roles=["user"])
    rotated = adapter.rotate(jti=jti)

    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=jti)  # 이미 rotate된 jti 재사용

    assert adapter.is_family_revoked(family_id) is True
    # 같은 family의 정상 jti(new_jti)로도 더 이상 rotate 불가
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=rotated.jti)


def test_rotate_unknown_jti_raises(adapter):
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti="unknown-jti")
