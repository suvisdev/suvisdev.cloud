from __future__ import annotations

import pytest

from auth import oauth_state_store as module
from auth.oauth_state_store import OAuthStateStore


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
def store(monkeypatch) -> OAuthStateStore:
    fake = _FakeRedis()
    monkeypatch.setattr(module.redis, "from_url", lambda *a, **k: fake)
    return OAuthStateStore()


def test_issued_state_returns_stored_aud_once(store):
    state = store.issue(aud="suvis-mova")
    data = store.consume(state)
    assert data.aud == "suvis-mova"
    assert data.return_to is None
    assert store.consume(state) is None  # 1회 소비 후 재사용 불가


def test_issued_state_carries_return_to(store):
    state = store.issue(aud="suvis-mova", return_to="/mova")
    data = store.consume(state)
    assert data.aud == "suvis-mova"
    assert data.return_to == "/mova"


def test_unknown_state_is_not_consumed(store):
    assert store.consume("never-issued") is None
