"""보도 유무 판정 — 차도 옆에 나란한 보도는 참, 가로지르는 횡단보도만 있으면 거짓."""

from __future__ import annotations

import pytest

pytest.importorskip("shapely")

from gildle.scripts.enrich_road_kind import enrich, sidewalk_flags  # noqa: E402


def _rec(a, b, hw, lat1, lng1, lat2, lng2):
    return {
        "from_node": a,
        "to_node": b,
        "highway": hw,
        "from_lat": lat1,
        "from_lng": lng1,
        "to_lat": lat2,
        "to_lng": lng2,
    }


# 동서로 뻗은 차도(약 440m). 0.0001° 위도 ≈ 11m.
ROAD = _rec("1", "2", "primary", 37.5000, 127.000, 37.5000, 127.005)
PARALLEL_WALK = _rec("3", "4", "footway", 37.5001, 127.000, 37.5001, 127.005)  # 11m 옆 나란히
CROSSING = _rec("5", "6", "footway", 37.4999, 127.0025, 37.5001, 127.0025)  # 가로지르는 22m
ALLEY = _rec("7", "8", "residential", 37.5100, 127.000, 37.5100, 127.001)


def test_parallel_sidewalk_counts_but_crossing_alone_does_not():
    assert sidewalk_flags([ROAD, PARALLEL_WALK, ALLEY]) == [True, False, False]
    assert sidewalk_flags([ROAD, CROSSING]) == [False, False]


def test_enrich_fills_highway_from_tags_and_reports():
    recs = [dict(ROAD, highway=None), dict(PARALLEL_WALK, highway=None)]
    stats = enrich(recs, {"1|2": "primary", "3|4": "footway"})
    assert recs[0]["highway"] == "primary" and recs[0]["sidewalk"] is True
    assert recs[1]["sidewalk"] is False
    assert (
        stats["car_edges"] == 1
        and stats["car_with_sidewalk"] == 1
        and stats["highway_missing"] == 0
    )
