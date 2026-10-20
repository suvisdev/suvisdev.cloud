from __future__ import annotations

from collections.abc import Callable

import pytest

from auth import refresh_store as module
from auth.refresh_store import (
    RefreshTokenStore,
    ReuseDetected,
)


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


class _FakeRedis:
    """dict 기반 최소 Redis 대체 — get/set(ex·nx)/delete. ex는 _FakeClock 기준으로 만료시킨다.

    `before_set`에 훅을 걸면 특정 set 직전에 다른 요청을 끼워 넣어 경합을 결정적으로 재현한다.
    """

    def __init__(self, clock: _FakeClock) -> None:
        self._clock = clock
        self._store: dict[str, tuple[str, float | None]] = {}
        self.before_set: Callable[[str, bool], None] | None = None

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool | None:
        hook, self.before_set = self.before_set, None
        if hook is not None:
            hook(key, nx)
        if nx and self.get(key) is not None:
            return None
        self._store[key] = (value, None if ex is None else self._clock() + ex)
        return True

    def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and self._clock() >= expires_at:
            del self._store[key]
            return None
        return value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.fixture()
def clock(monkeypatch) -> _FakeClock:
    c = _FakeClock()
    monkeypatch.setattr(module, "_now", c)
    return c


@pytest.fixture()
def fake(clock) -> _FakeRedis:
    return _FakeRedis(clock)


@pytest.fixture()
def adapter(monkeypatch, fake) -> RefreshTokenStore:
    monkeypatch.setattr(module.redis, "from_url", lambda *a, **k: fake)
    return RefreshTokenStore()


def _issue(adapter: RefreshTokenStore) -> tuple[str, str]:
    return adapter.issue(sub="42", aud="suvis-mova", roles=["user"])


def test_issue_then_rotate_succeeds(adapter):
    jti, family_id = _issue(adapter)
    rotated = adapter.rotate(jti=jti)
    assert rotated.family_id == family_id
    assert rotated.jti != jti
    assert rotated.sub == "42"
    assert rotated.aud == "suvis-mova"
    assert rotated.roles == ["user"]


def test_reusing_rotated_jti_after_grace_raises_and_revokes_family(adapter, clock):
    jti, family_id = _issue(adapter)
    rotated = adapter.rotate(jti=jti)
    clock.t += 11  # 10초 유예가 지난 뒤의 재사용

    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=jti)

    assert adapter.is_family_revoked(family_id) is True
    # 같은 family의 정상 jti(new_jti)로도 더 이상 rotate 불가
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=rotated.jti)


def test_rotate_unknown_jti_raises(adapter):
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti="unknown-jti")


def test_sequential_duplicate_within_grace_returns_same_new_token(adapter, clock):
    jti, family_id = _issue(adapter)
    first = adapter.rotate(jti=jti)
    clock.t += 9.9
    assert adapter.rotate(jti=jti) == first
    assert adapter.is_family_revoked(family_id) is False
    assert adapter.rotate(jti=first.jti).family_id == family_id  # 계열은 계속 쓸 수 있다


def test_grace_boundary_10s_then_revokes(adapter, clock):
    jti, family_id = _issue(adapter)
    first = adapter.rotate(jti=jti)
    clock.t += 10
    assert adapter.rotate(jti=jti) == first  # 10초까지는 유예
    clock.t += 0.1
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=jti)
    assert adapter.is_family_revoked(family_id) is True


def test_concurrent_rotate_interleaved_at_claim_issues_one_successor(adapter, fake):
    """두 요청이 모두 '미회전'을 읽은 뒤 서로의 claim 직전에 끼어든 경합 — 하나만 회전한다."""
    jti, family_id = _issue(adapter)
    inner: list[object] = []

    def _other_request(key: str, nx: bool) -> None:
        # 바깥 요청이 후속 토큰을 저장하려는 순간, 안쪽 요청이 처음부터 끝까지 회전한다.
        if key.startswith("auth:refresh:") and not nx:
            inner.append(adapter.rotate(jti=jti))

    fake.before_set = _other_request
    outer = adapter.rotate(jti=jti)

    assert inner and outer == inner[0]  # 둘 다 같은 후속 토큰
    assert adapter.is_family_revoked(family_id) is False
    successors = [
        k
        for k in fake._store
        if k.startswith("auth:refresh:")
        and not k.startswith("auth:refresh:claim:")
        and k != f"auth:refresh:{jti}"
    ]
    assert successors == [f"auth:refresh:{outer.jti}"]  # 진 쪽 후속 토큰은 지워짐


def test_concurrent_rotate_loser_after_successor_saved(adapter, fake):
    """바깥 요청이 후속 토큰을 저장한 뒤 claim NX 직전에 안쪽 요청이 이긴 경우."""
    jti, family_id = _issue(adapter)
    inner: list[object] = []

    def _other_request(key: str, nx: bool) -> None:
        if nx:
            fake.before_set = None
            inner.append(adapter.rotate(jti=jti))

    def _arm(key: str, nx: bool) -> None:  # 첫 set(후속 토큰 저장)은 통과, 다음 set(NX)에 끼움
        fake.before_set = _other_request

    fake.before_set = _arm
    outer = adapter.rotate(jti=jti)
    assert inner and outer == inner[0]
    assert adapter.is_family_revoked(family_id) is False


def test_late_duplicate_after_successor_rotated_is_rejected_without_revoking(adapter, clock):
    """A→B→C 뒤 늦게 온 A — 이미 쓴 B를 돌려주지 않고(쿠키 덮어쓰기 방지) 401만, 계열은 유지."""
    a, family_id = _issue(adapter)
    b = adapter.rotate(jti=a)
    c = adapter.rotate(jti=b.jti)
    clock.t += 1

    with pytest.raises(ReuseDetected):
        adapter.rotate(jti=a)
    assert adapter.is_family_revoked(family_id) is False
    d = adapter.rotate(jti=c.jti)  # 현재 쿠키(C)로는 계속 정상 회전
    assert d.family_id == family_id


def test_legacy_used_record_is_still_treated_as_reuse(adapter, fake):
    """claim 도입 전에 회전돼 used=True로 남은 토큰 재사용은 기존대로 계열 폐기."""
    fake.set(
        "auth:refresh:old-used",
        '{"sub": "42", "aud": "suvis-mova", "roles": ["user"], "family_id": "f", "used": true}',
    )
    with pytest.raises(ReuseDetected):
        adapter.rotate(jti="old-used")
    assert adapter.is_family_revoked("f") is True


def test_claim_and_tokens_expire_with_refresh_ttl(adapter, clock):
    jti, _ = _issue(adapter)
    adapter.rotate(jti=jti)
    clock.t += 14 * 24 * 3600
    with pytest.raises(ReuseDetected):  # 만료 후엔 토큰 자체가 없다
        adapter.rotate(jti=jti)


def test_new_sessions_carry_version_and_old_ones_rotate_as_legacy(adapter, fake):
    jti, _ = _issue(adapter)
    assert adapter.rotate(jti=jti).legacy is False

    fake.set(  # 배포 전 형식(sv 없음)
        "auth:refresh:old",
        '{"sub": "1", "aud": "suvis-mova", "roles": ["admin"], "family_id": "f", "used": false}',
    )
    assert adapter.rotate(jti="old").legacy is True
