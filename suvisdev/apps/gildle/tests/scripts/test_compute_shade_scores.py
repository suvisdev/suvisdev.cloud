"""그림자 캐스팅·엣지 교차의 기하 검증 — 합성 데이터."""

from __future__ import annotations

import pytest

# shapely는 오프라인 파이프라인 전용이라 서빙 이미지에 없다 — 파드에서 전체
# 테스트를 돌릴 때 수집 단계에서 깨지지 않게 건너뛴다(2026-09-22).
pytest.importorskip("shapely")

from gildle.scripts.compute_shade_scores import (  # noqa: E402
    compute_slot_fractions,
    project_to_meters,
)

# 원점(37.53, 126.93) 근처 20m×20m, 높이 30m 건물 하나.
_BUILDING = {
    "outline": [
        [37.5300, 126.9300],
        [37.5300, 126.93023],  # 동쪽으로 약 20m
        [37.53018, 126.93023],  # 북쪽으로 약 20m
        [37.53018, 126.9300],
    ],
    "height_m": 30.0,
}


def _edge(from_lat, from_lng, to_lat, to_lng, key):
    return {
        "from_node": key + "a",
        "to_node": key + "b",
        "from_lat": from_lat,
        "from_lng": from_lng,
        "to_lat": to_lat,
        "to_lng": to_lng,
        "base_distance_m": 30.0,
        "tree_score": 0.0,
    }


def test_morning_shadow_falls_west():
    # 아침(태양 동쪽) → 그림자는 건물 서쪽. 서쪽 15m 지점의 남북 방향 엣지는
    # 그늘, 동쪽 15m 지점의 엣지는 햇빛이어야 한다.
    west_edge = _edge(37.5300, 126.92983, 37.53018, 126.92983, "w")
    east_edge = _edge(37.5300, 126.93040, 37.53018, 126.93040, "e")
    fr = compute_slot_fractions(
        edges=[west_edge, east_edge],
        buildings=[_BUILDING],
        sun_alt_deg=30.0,
        sun_az_deg=90.0,  # 정동, 고도 30° → 그림자 길이 약 52m
    )
    assert fr["wa-wb"] > 60  # 서쪽 엣지: 대부분 그늘
    assert fr["ea-eb"] == 0  # 동쪽 엣지: 햇빛


def test_tree_score_adds_shade():
    sunny = _edge(37.5300, 126.93040, 37.53018, 126.93040, "t")
    sunny["tree_score"] = 0.5
    fr = compute_slot_fractions(edges=[sunny], buildings=[], sun_alt_deg=60.0, sun_az_deg=180.0)
    assert fr["ta-tb"] == 30  # 0.6 × 0.5 = 0.3 → 30%


def test_low_sun_means_full_shade():
    edge = _edge(37.5300, 126.93040, 37.53018, 126.93040, "n")
    fr = compute_slot_fractions(edges=[edge], buildings=[], sun_alt_deg=3.0, sun_az_deg=270.0)
    assert fr["na-nb"] == 100  # 고도 5° 이하 — 전면 그늘 취급


def test_project_roundtrip_scale():
    # 위도 1e-4°(≈11.1m)가 미터 좌표에서 10~12m로 투영되는지.
    x0, y0 = project_to_meters(37.5300, 126.9300, 37.53, 126.93)
    x1, y1 = project_to_meters(37.5301, 126.9300, 37.53, 126.93)
    assert abs((y1 - y0) - 11.1) < 1.0 and abs(x1 - x0) < 0.01


def test_impute_heights_uses_cell_median():
    from gildle.scripts.compute_shade_scores import impute_heights

    # 같은 250m 격자 안: 실측 20m·40m 두 동 + 결측 한 동 → 중앙값 30m.
    def _b(lng_off: float, height: float, known: bool):
        base = [
            [37.5300, 126.9300 + lng_off],
            [37.5300, 126.93005 + lng_off],
            [37.53005, 126.93005 + lng_off],
        ]
        return {"outline": base, "height_m": height, "height_known": known}

    buildings = [
        _b(0.0, 20.0, True),
        _b(0.0001, 40.0, True),
        _b(0.0002, 6.0, False),
        _b(0.0003, 25.0, True),
    ]
    imputed = impute_heights(buildings)
    assert imputed == 1
    assert buildings[2]["height_m"] == 25.0  # [20, 25, 40]의 중앙값


def test_impute_heights_falls_back_to_global_median():
    from gildle.scripts.compute_shade_scores import impute_heights

    known_far = {
        "outline": [[37.60, 127.10], [37.60, 127.1001], [37.6001, 127.1001]],
        "height_m": 12.0,
        "height_known": True,
    }
    unknown = {
        "outline": [[37.45, 126.80], [37.45, 126.8001], [37.4501, 126.8001]],
        "height_m": 6.0,
        "height_known": False,
    }
    # 결측 건물의 격자엔 실측 표본이 없음(최소 3동 미달) → 전역 중앙값 12.0.
    impute_heights([known_far, unknown])
    assert unknown["height_m"] == 12.0
