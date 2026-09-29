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


def test_rules_destination_makes_route_and_is_not_a_stop():
    r = parse_rules("강아지 병원으로 가는 최단 경로 알려줘")
    assert (r.kind, r.destination, r.preference, r.stops) == ("route", "동물병원", "fast", ())
    assert parse_rules("가장 가까운 애견카페로 가자").destination == "애견카페"
    home = parse_rules("병원 들렀다가 집으로 올래")  # 집으로 → 루프, 병원은 들를 곳
    assert (home.kind, home.destination, home.stops) == ("loop", None, ("동물병원",))
    assert parse_rules("오늘은 그늘로만 산책하고 싶어").kind == "loop"


def test_verify_destination_needs_sentence_evidence():
    ok = verify({"kind": "route", "destination": "동물병원"}, "병원 가는 길 알려줘")
    assert (ok.kind, ok.destination) == ("route", "동물병원")
    r = verify({"kind": "route", "destination": "동물병원"}, "빨리 가는 길")
    assert r.destination is None  # 문장에 근거 없는 목적지는 버린다
    r = verify({"kind": "loop", "destination": None}, "동물병원까지 빠른 길")
    assert (r.kind, r.destination) == ("route", "동물병원")  # 규칙 목적지가 우선


def test_form_end_coordinates_override_destination():
    base = parse_rules("동물병원으로 가는 길")
    kw = dict(minutes=None, distance_km=None, preference=None, stops=None, has_text=True)
    picked = apply_form(base, has_end=True, **kw)
    assert (picked.kind, picked.destination) == ("route", None)
    spoken = apply_form(base, has_end=False, **kw)
    assert (spoken.kind, spoken.destination) == ("route", "동물병원")
