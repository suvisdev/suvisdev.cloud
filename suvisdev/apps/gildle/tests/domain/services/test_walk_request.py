"""산책 요청 이해 — 규칙 파서·모델 슬롯 검증·폼 우선(2026-09-28)."""

from __future__ import annotations

from gildle.domain.services.walk_request import WalkRequest, apply_form, parse_rules, verify


def test_rules_parse_minutes_km_preference_and_stops():
    r = parse_rules("오늘은 40분 동안 3키로 정도 편하게 걷고 집에 올래, 가는 길에 사료도 사고")
    assert (r.kind, r.minutes, r.distance_km, r.preference) == ("loop", 40, 3.0, "flat")
    assert r.stops == ("용품점",)
    assert parse_rules("한시간 반 언덕길로 운동").minutes == 90
    assert parse_rules("언덕 있는 길로 1시간").preference == "hilly"
    assert parse_rules("500미터만").distance_km == 0.5


def test_rules_default_and_clamp():
    r = parse_rules("")
    assert r.minutes is None and r.distance_km is None and r.preference == "flat"
    assert parse_rules("1000분").minutes == 180
    assert parse_rules("99km").distance_km == 15.0


def test_verify_trusts_sentence_numbers_and_keywords_over_model():
    llm = {"kind": "loop", "minutes": 20, "distance_km": 9, "preference": "fast", "stops": []}
    r = verify(llm, "30분 동안 언덕길로")
    assert r.minutes == 30  # 문장 근거
    assert r.preference == "hilly"  # 키워드 근거
    assert r.distance_km == 9.0  # 문장에 없으니 모델 값
    assert r.source == "llm" and "minutes:rules" in r.notes


def test_verify_uses_model_for_expressions_rules_miss_and_drops_invalid():
    llm = {"minutes": 45, "preference": "green", "stops": ["동물병원", "노래방"], "kind": "x"}
    r = verify(llm, "사십오 분쯤 강아지랑 기분 좋게")
    assert r.minutes == 45 and r.preference == "green"
    assert r.stops == ("동물병원",) and r.kind == "loop"
    assert verify({"preference": "zzz", "minutes": "많이"}, "산책").preference == "flat"


def test_form_overrides_understanding():
    base = WalkRequest(minutes=30, distance_km=2.0, preference="flat", source="llm")
    r = apply_form(
        base,
        minutes=60,
        distance_km=None,
        preference="hilly",
        stops=["펫샵"],
        has_end=False,
        has_text=True,
    )
    assert (r.minutes, r.distance_km, r.preference, r.stops, r.source) == (
        60,
        2.0,
        "hilly",
        ("펫샵",),
        "llm",
    )


def test_targets_time_caps_distance():
    assert WalkRequest(minutes=30).targets() == (30 * 60 * 1.2 * 0.95, 30 * 60 * 1.2)
    target, cap = WalkRequest(minutes=20, distance_km=3).targets()
    assert target == cap == 20 * 60 * 1.2  # 3km는 20분에 못 걸으니 시간에 맞춘다
    assert WalkRequest(distance_km=2).targets() == (2000, None)
