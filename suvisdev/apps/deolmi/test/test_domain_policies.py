from __future__ import annotations

import pytest
from fakes import BOT, ENTER_SUBMIT_HUMAN, HUMAN, KEYBOARD_HUMAN, TOUCH_HUMAN

from deolmi.domain.services.origin_policy import host_of, origin_allowed
from deolmi.domain.services.scoring_policy import (
    FEATURE_ORDER,
    VELOCITY_BURST,
    VELOCITY_SUSPECT,
    no_mouse_input,
    rule_score,
    to_features,
    verdict_of,
)
from deolmi.domain.services.site_keys import (
    hash_secret,
    new_secret_key,
    new_site_key,
    secret_matches,
)


def test_human_signals_trip_no_rule():
    r = rule_score(HUMAN, velocity_count=1)
    assert r.score == 0.0 and r.reasons == ()


def test_bot_signals_take_highest_rule_and_keep_every_reason():
    r = rule_score(BOT, velocity_count=1)
    assert r.score == 0.95
    assert len(r.reasons) == 3  # 키 간격·클릭 간격·직선 이동


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        ({**HUMAN, "move_count": 0}, 0.80),  # 마우스 없이 클릭
        ({**HUMAN, "dwell_ms": 200}, 0.75),  # 제출이 너무 빠름
    ],
)
def test_single_rules(signals, expected):
    assert rule_score(signals, velocity_count=1).score == expected


def test_velocity_thresholds():
    assert rule_score(HUMAN, VELOCITY_SUSPECT - 1).score == 0.0
    assert rule_score(HUMAN, VELOCITY_SUSPECT).score == 0.60
    assert rule_score(HUMAN, VELOCITY_BURST).score == 0.75


def test_velocity_alone_never_blocks():
    # PC방·회사 NAT: 사람 수백 명이 IP 하나 — 속도만으로는 challenge까지만.
    r = rule_score(HUMAN, velocity_count=10_000)
    assert verdict_of(r.score) == "challenge" and r.reasons


@pytest.mark.parametrize("signals", [TOUCH_HUMAN, KEYBOARD_HUMAN, ENTER_SUBMIT_HUMAN])
def test_touch_and_keyboard_humans_trip_no_rule(signals):
    assert rule_score(signals, velocity_count=1).score == 0.0
    assert no_mouse_input(signals)


def test_click_without_any_movement_or_keyboard_still_flagged():
    # 터치도 키보드 클릭도 없이 움직임 없는 클릭 — 스크립트의 el.click()·좌표 클릭.
    s = {**KEYBOARD_HUMAN, "kbd_click_count": 0}
    assert rule_score(s, velocity_count=1).score == 0.80
    assert not no_mouse_input(s)
    # 키보드 클릭 1번에 마우스 아닌 클릭이 더 있으면 여전히 의심.
    assert rule_score({**KEYBOARD_HUMAN, "click_count": 3, "click_iv_std": 300}, 1).score == 0.80


def test_missing_counts_do_not_trigger_interval_rules():
    # 키/클릭이 없으면 간격 std가 0이어도 '기계적'으로 보지 않는다.
    assert rule_score({"move_count": 50, "path_px": 900, "straightness": 0.4}, 1).score == 0.0


def test_verdict_bands():
    assert verdict_of(0.54) == "allow"
    assert verdict_of(0.55) == "challenge"
    assert verdict_of(0.80) == "block"


def test_features_follow_fixed_order_and_fill_missing_with_zero():
    v = to_features({"dwell_ms": 10, "move_count": 3})
    assert len(v) == len(FEATURE_ORDER)
    assert v[0] == 3 and v[-1] == 10 and v[1] == 0


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("https://ticket.example.com", True),
        ("https://www.ticket.example.com:8443", True),  # 서브도메인·포트
        ("https://evil.com", False),
        ("https://notticket.example.com.evil.com", False),
        (None, False),  # 등록 도메인이 있으면 Origin 필수
    ],
)
def test_origin_policy(origin, allowed):
    assert origin_allowed(origin, ("ticket.example.com",)) is allowed


def test_origin_policy_skips_when_no_domains():
    assert origin_allowed(None, ())


def test_host_of():
    assert host_of("HTTPS://A.Example.com:443/x") == "a.example.com"


def test_site_keys():
    pk, sk = new_site_key(), new_secret_key()
    assert pk.startswith("pk_") and sk.startswith("sk_") and pk != new_site_key()
    assert secret_matches(sk, hash_secret(sk))
    assert not secret_matches(sk + "x", hash_secret(sk))
