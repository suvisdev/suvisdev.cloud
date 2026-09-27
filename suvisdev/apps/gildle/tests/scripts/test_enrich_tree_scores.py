"""enrich_tree_scores — 수관 폴리곤·나무열·나무 점이 간선 tree_score에 반영되는지."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("shapely")  # 서빙 이미지엔 shapely가 없다(compute_shade_scores와 같은 이유)

from gildle.scripts.enrich_tree_scores import (  # noqa: E402
    CanopyScorer,
    _edge_line,
    enrich,
    load_canopy,
    load_tree_points,
)


def _rec(from_lat, from_lng, to_lat, to_lng, tree=0.0):
    return {
        "from_node": "a",
        "to_node": "b",
        "base_distance_m": 100.0,
        "midpoint_lat": (from_lat + to_lat) / 2,
        "midpoint_lng": (from_lng + to_lng) / 2,
        "from_lat": from_lat,
        "from_lng": from_lng,
        "to_lat": to_lat,
        "to_lng": to_lng,
        "tree_score": tree,
        "hazard_score": 0.0,
        "dog_friendly_score": 0.3,
    }


@pytest.fixture
def scorer(tmp_path):
    # 숲 폴리곤(37.500~37.502 × 127.000~127.002), 그 남쪽으로 1km 떨어진 공원,
    # 동쪽 멀리 나무열 하나, 그리고 나무 점 10개가 12m 간격으로 늘어선 거리.
    canopy = [
        {
            "kind": "wood",
            "id": "w1",
            "outline": [
                [37.500, 127.000],
                [37.502, 127.000],
                [37.502, 127.002],
                [37.500, 127.002],
                [37.500, 127.000],
            ],
        },
        {
            "kind": "park",
            "id": "w2",
            "outline": [
                [37.490, 127.000],
                [37.492, 127.000],
                [37.492, 127.002],
                [37.490, 127.002],
                [37.490, 127.000],
            ],
        },
        {"kind": "tree_row", "id": "w3", "line": [[37.520, 127.010], [37.520, 127.012]]},
    ]
    trees = [
        {"type": "node", "id": i, "lat": 37.530, "lon": 127.020 + i * 0.000135} for i in range(10)
    ]
    cp = tmp_path / "canopy.json"
    tp = tmp_path / "trees.json"
    cp.write_text(json.dumps(canopy), encoding="utf-8")
    tp.write_text(json.dumps(trees), encoding="utf-8")
    polys, kinds, rows = load_canopy(cp)
    return CanopyScorer(polys, kinds, rows, load_tree_points(tp))


def test_edge_inside_wood_gets_full_canopy(scorer):
    score, near_park = scorer.score(_edge_line(_rec(37.5005, 127.0005, 37.5015, 127.0015)))
    assert score == 1.0
    assert near_park is False


def test_edge_inside_park_gets_park_score_and_dog_boost(scorer):
    score, near_park = scorer.score(_edge_line(_rec(37.4905, 127.0005, 37.4915, 127.0015)))
    assert score == 0.6
    assert near_park is True


def test_tree_row_and_point_density(scorer):
    # 나무열과 나란한 거리(5m 옆)
    row_score, _ = scorer.score(_edge_line(_rec(37.52004, 127.010, 37.52004, 127.012)))
    assert row_score == 0.9
    # 나무 점 10개가 12m 간격 → 길이 108m 거리에 만점
    pts_score, _ = scorer.score(_edge_line(_rec(37.530, 127.020, 37.530, 127.0212)))
    assert pts_score == 1.0
    # 아무것도 없는 곳
    assert scorer.score(_edge_line(_rec(37.600, 127.100, 37.601, 127.100)))[0] == 0.0


def test_enrich_keeps_existing_as_floor_and_is_idempotent(scorer):
    recs = [
        _rec(37.5005, 127.0005, 37.5015, 127.0015, tree=0.2),  # 숲 → 1.0
        _rec(37.600, 127.100, 37.601, 127.100, tree=0.35),  # 원천 없음 → 기존 0.35 유지
    ]
    stats = enrich(recs, scorer)
    assert [r["tree_score"] for r in recs] == [1.0, 0.35]
    assert recs[0]["dog_friendly_score"] == 1.0  # 1.0×0.7+0.3
    assert recs[1]["dog_friendly_score"] == pytest.approx(0.35 * 0.7 + 0.3)
    assert stats["tree_positive_after"] == 2
    again = enrich([dict(r) for r in recs], scorer)
    assert again["changed"] == 0
