from __future__ import annotations

import pytest
from fakes import HUMAN, _FakeRedis

from deolmi.adapter.outbound.cache.redis_velocity_adapter import RedisVelocityAdapter
from deolmi.adapter.outbound.ml.isolation_forest_model_adapter import IsolationForestModelAdapter
from deolmi.adapter.outbound.repositories.event_pg_repository import EventPgLogWriter
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.dtos.score_dto import ScoreResultDto
from deolmi.app.errors import (
    TokenExpiredError,
    TokenInvalidError,
    TokenReusedError,
    TokenStoreUnavailableError,
)
from deolmi.domain.services.scoring_policy import to_features


def test_token_roundtrip_and_single_use():
    fake = _FakeRedis()
    tokens = JwtScoreTokenAdapter("s1", fake)
    p = tokens.decode(tokens.issue("pk_a", {"verdict": "allow"}))
    assert p.site_key == "pk_a" and p.result == {"verdict": "allow"}
    tokens.consume(p)
    with pytest.raises(TokenReusedError):
        tokens.consume(p)
    assert 0 < fake.ttl[f"deolmi:jti:{p.jti}"] <= 121  # 토큰 만료까지만 기억


def test_used_token_stays_used_across_processes():
    # 노트북↔집컴 서빙 전환·재시작: 새 어댑터(새 프로세스)라도 같은 Redis를 보면 재사용이 막힌다.
    shared = _FakeRedis()
    issuer = JwtScoreTokenAdapter("s1", shared)
    p = issuer.decode(issuer.issue("pk_a", {}))
    issuer.consume(p)
    with pytest.raises(TokenReusedError):
        JwtScoreTokenAdapter("s1", shared).consume(p)


def test_token_store_down_fails_closed():
    fake = _FakeRedis()
    tokens = JwtScoreTokenAdapter("s1", fake)
    p = tokens.decode(tokens.issue("pk_a", {}))
    fake.down = True
    with pytest.raises(TokenStoreUnavailableError):
        tokens.consume(p)


def test_token_signed_with_other_secret_is_invalid():
    forged = JwtScoreTokenAdapter("attacker", _FakeRedis()).issue("pk_a", {"verdict": "allow"})
    with pytest.raises(TokenInvalidError):
        JwtScoreTokenAdapter("s1", _FakeRedis()).decode(forged)


def test_tampered_token_is_invalid():
    t = JwtScoreTokenAdapter("s1", _FakeRedis()).issue("pk_a", {"verdict": "block"})
    head, body, sig = t.split(".")
    with pytest.raises(TokenInvalidError):
        JwtScoreTokenAdapter("s1", _FakeRedis()).decode(f"{head}.{body}x.{sig}")


def test_expired_token():
    t = JwtScoreTokenAdapter("s1", _FakeRedis(), ttl_s=-1).issue("pk_a", {})
    with pytest.raises(TokenExpiredError):
        JwtScoreTokenAdapter("s1", _FakeRedis()).decode(t)


def test_velocity_counts_within_window_per_key():
    fake = _FakeRedis()
    v = RedisVelocityAdapter(fake, window_s=3600)
    assert [v.record("a") for _ in range(3)] == [1, 2, 3]
    assert v.record("b") == 1
    assert set(fake.ttl.values()) == {3601}  # 창이 끝나면 키가 사라진다


def test_velocity_redis_down_fails_open():
    fake = _FakeRedis()
    fake.down = True
    assert RedisVelocityAdapter(fake).record("a") == 0


def test_bootstrap_model_separates_human_from_scripted(tmp_path):
    model = IsolationForestModelAdapter(path=tmp_path / "absent.joblib")
    assert model.source == "bootstrap"
    human = model.score(to_features(HUMAN))
    # 붙여넣기·즉시 제출하는 스크립트: 규칙 일부는 피해도 분포에서 멀다.
    scripted = model.score(
        to_features(
            {
                "move_count": 2,
                "path_px": 60,
                "straightness": 0.9,
                "click_iv_mean": 30,
                "click_iv_std": 9,
                "key_iv_std": 5,
                "dwell_ms": 400,
            }
        )
    )
    assert human < 0.55 < 0.80 < scripted


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = self.closed = False

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.closed = True

    def add(self, row: object) -> None:
        self.added.append(row)

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_log_writer_opens_a_fresh_session_per_event():
    # 응답 뒤(BackgroundTasks)에는 요청 세션이 닫혀 있을 수 있다 — 쓸 때마다 새 세션.
    sessions: list[_FakeSession] = []

    def factory() -> _FakeSession:
        sessions.append(_FakeSession())
        return sessions[-1]

    writer = EventPgLogWriter(factory)  # type: ignore[arg-type]
    result = ScoreResultDto(0.1, "allow", 0.0, 0.1, "model", [])
    await writer.add(1, "1.2.3.4", HUMAN, result)
    await writer.add(1, "1.2.3.4", HUMAN, result)
    assert len(sessions) == 2
    assert all(s.committed and s.closed and len(s.added) == 1 for s in sessions)
