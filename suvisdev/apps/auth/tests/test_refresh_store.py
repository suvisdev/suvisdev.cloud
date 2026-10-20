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
    adapter._client.delete(f"auth:refresh:grace:{jti}")  # 10초 유예가 지난 뒤의 재사용

    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=jti)  # 이미 rotate된 jti 재사용

    assert adapter.is_family_revoked(family_id) is True
    # 같은 family의 정상 jti(new_jti)로도 더 이상 rotate 불가
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=rotated.jti)


def test_rotate_unknown_jti_raises(adapter):
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti="unknown-jti")


def test_near_simultaneous_reuse_within_grace_returns_same_new_token(adapter):
    """BFF 다중 인스턴스가 같은 refresh를 거의 동시에 보내면 계열을 폐기하지 않고 같은 결과."""
    jti, family_id = adapter.issue(sub="42", aud="suvis-mova", roles=["user"])
    first = adapter.rotate(jti=jti)
    second = adapter.rotate(jti=jti)  # 유예(10초) 안
    assert second == first
    assert adapter.is_family_revoked(family_id) is False
    assert adapter.rotate(jti=first.jti).family_id == family_id  # 계열은 계속 쓸 수 있다


def test_grace_is_stored_with_short_ttl(adapter, monkeypatch):
    calls: list[tuple[str, int | None]] = []
    original = adapter._client.set

    def _spy(key, value, ex=None):
        calls.append((key, ex))
        original(key, value, ex=ex)

    monkeypatch.setattr(adapter._client, "set", _spy)
    jti, _ = adapter.issue(sub="42", aud="suvis-mova", roles=["user"])
    adapter.rotate(jti=jti)
    assert (f"auth:refresh:grace:{jti}", 10) in calls


def test_new_sessions_carry_version_and_old_ones_rotate_as_legacy(adapter):
    jti, _ = adapter.issue(sub="42", aud="suvis-mova", roles=["user"])
    assert adapter.rotate(jti=jti).legacy is False

    adapter._client.set(  # 배포 전 형식(sv 없음)
        "auth:refresh:old",
        '{"sub": "1", "aud": "suvis-mova", "roles": ["admin"], "family_id": "f", "used": false}',
    )
    assert adapter.rotate(jti="old").legacy is True
