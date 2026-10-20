from __future__ import annotations

import pytest
from fakes import HUMAN

from deolmi.adapter.outbound.memory.sliding_window_velocity_adapter import (
    SlidingWindowVelocityAdapter,
)
from deolmi.adapter.outbound.ml.isolation_forest_model_adapter import IsolationForestModelAdapter
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.errors import TokenExpiredError, TokenInvalidError, TokenReusedError
from deolmi.domain.services.scoring_policy import to_features


def test_token_roundtrip_and_single_use():
    tokens = JwtScoreTokenAdapter("s1")
    p = tokens.decode(tokens.issue("pk_a", {"verdict": "allow"}))
    assert p.site_key == "pk_a" and p.result == {"verdict": "allow"}
    tokens.consume(p)
    with pytest.raises(TokenReusedError):
        tokens.consume(p)


def test_token_signed_with_other_secret_is_invalid():
    forged = JwtScoreTokenAdapter("attacker").issue("pk_a", {"verdict": "allow"})
    with pytest.raises(TokenInvalidError):
        JwtScoreTokenAdapter("s1").decode(forged)


def test_tampered_token_is_invalid():
    t = JwtScoreTokenAdapter("s1").issue("pk_a", {"verdict": "block"})
    head, body, sig = t.split(".")
    with pytest.raises(TokenInvalidError):
        JwtScoreTokenAdapter("s1").decode(f"{head}.{body}x.{sig}")


def test_expired_token():
    t = JwtScoreTokenAdapter("s1", ttl_s=-1).issue("pk_a", {})
    with pytest.raises(TokenExpiredError):
        JwtScoreTokenAdapter("s1").decode(t)


def test_velocity_counts_within_window_per_key():
    v = SlidingWindowVelocityAdapter(window_s=60)
    assert [v.record("a") for _ in range(3)] == [1, 2, 3]
    assert v.record("b") == 1


def test_velocity_window_expires():
    v = SlidingWindowVelocityAdapter(window_s=0)
    v.record("a")
    assert v.record("a") == 1


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
