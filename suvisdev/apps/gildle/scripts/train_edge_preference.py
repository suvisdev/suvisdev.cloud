"""모델 A — 간선 선호 가중치를 손튜닝 상수 대신 실제 산책 기록(`walks`)에서 학습한다.

지금 여름 규칙은 `거리 × (1 + 4·(1−그늘))` 처럼 사람이 정한 상수다. 사용자가 실제로
걸은 경로가 쌓이면 "추천 경로 vs 실제 경로"의 차이가 라벨이 된다:

  걸은 경로의 간선           → 양성(1)
  같은 출발·도착의 최단거리 경로 중 걷지 않은 간선 → 음성(0)   (반사실 후보)
  특징 = [그늘, 가로수, 위험, log 길이]  → 로지스틱 회귀
  계수 β_shade > 0 이면 "그늘을 위해 돌아간다"는 뜻이고, 페널티 배율은
  exp(−β)로 환산한다(`_docs/GILDLE_ROUTING_ALGORITHM.md` §2-A).

데이터가 아직 0건이라(2026-09-22) 실제 학습은 못 한다. 대신 **파이프라인이 도는지**를
합성 세계에서 검증한다: 그늘 거리를 선호해 걷는 가상 사용자의 walks를 만들어 넣고
학습 계수가 그 방향으로 나오는지 본다.

    python -m gildle.scripts.train_edge_preference --synthetic          # 가상 데이터 검증
    python -m gildle.scripts.train_edge_preference --walks walks.json  # 실데이터(추후)
      walks.json: [{"path": [[lat,lng],...], "season_mode": "summer", "started_at": "..."}]
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from gildle.adapter.outbound.graph.dijkstra_route_graph_adapter import (
    DijkstraRouteGraphAdapter,
)
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

_MATCH_M = 25.0  # 기록 좌표를 간선에 붙이는 반경
FEATURES = ["shade", "tree", "hazard", "log_len"]


# ── 기록 → 간선 매칭 ────────────────────────────────────────────────────────


def match_path_to_edges(points: list[list[float]], edges: list[RouteEdge]) -> list[RouteEdge]:
    """기록 좌표열을 가장 가까운 간선(중점 기준, 25m 이내)에 순서대로 붙인다. 중복 제거."""
    matched: list[RouteEdge] = []
    for lat, lng in points:
        c = Coordinate(latitude=lat, longitude=lng)
        best, best_d = None, _MATCH_M
        for e in edges:
            d = e.midpoint.distance_to(c)
            if d < best_d:
                best, best_d = e, d
        if best is not None and (not matched or matched[-1] is not best):
            matched.append(best)
    return matched


def _endpoints(edges_walked: list[RouteEdge]) -> tuple[str, str]:
    first, last = edges_walked[0], edges_walked[-1]
    return first.from_node, last.to_node


def build_examples(
    walks: list[dict[str, Any]],
    edges: list[RouteEdge],
    shade_lookup: Mapping[tuple[str, str], float] | None,
) -> list[tuple[list[float], int]]:
    """walk마다 (걸은 간선=1, 최단거리 반사실 경로의 걷지 않은 간선=0) 예시를 만든다."""
    adapter = DijkstraRouteGraphAdapter()
    graph = adapter.build_graph(edges)

    def feat(e: RouteEdge) -> list[float]:
        shade = 0.0
        if shade_lookup is not None:
            shade = shade_lookup.get(
                (e.from_node, e.to_node), shade_lookup.get((e.to_node, e.from_node), 0.0)
            )
        return [shade, e.tree_score, e.hazard_score, math.log(max(e.base_distance_m, 1.0))]

    lookup: dict[tuple[str, str], RouteEdge] = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e

    out: list[tuple[list[float], int]] = []
    for w in walks:
        walked = match_path_to_edges(w["path"], edges)
        if len(walked) < 2:
            continue
        s, t = _endpoints(walked)
        counter = adapter.find_shortest_path(graph, s, t, lambda e: e.base_distance_m)
        counter_edges = {id(lookup[(counter[i], counter[i + 1])]) for i in range(len(counter) - 1)}
        walked_ids = {id(e) for e in walked}
        for e in walked:
            out.append((feat(e), 1))
        for i in range(len(counter) - 1):
            e = lookup[(counter[i], counter[i + 1])]
            if id(e) in counter_edges and id(e) not in walked_ids:
                out.append((feat(e), 0))
    return out


# ── 학습 ────────────────────────────────────────────────────────────────────


def fit_logistic(
    examples: list[tuple[list[float], int]], epochs: int = 300, lr: float = 0.1
) -> list[float]:
    """의존성 없는 경사하강 로지스틱 회귀(특징 표준화 포함). sklearn이 있으면 그걸 써도 된다."""
    n_feat = len(FEATURES)
    xs = [x for x, _ in examples]
    ys = [y for _, y in examples]
    mean = [sum(x[j] for x in xs) / len(xs) for j in range(n_feat)]
    std = [
        max(1e-6, (sum((x[j] - mean[j]) ** 2 for x in xs) / len(xs)) ** 0.5) for j in range(n_feat)
    ]
    z = [[(x[j] - mean[j]) / std[j] for j in range(n_feat)] for x in xs]
    w = [0.0] * n_feat
    b = 0.0
    for _ in range(epochs):
        gw = [0.0] * n_feat
        gb = 0.0
        for row, y in zip(z, ys, strict=True):
            p = 1.0 / (1.0 + math.exp(-(sum(w[j] * row[j] for j in range(n_feat)) + b)))
            err = p - y
            for j in range(n_feat):
                gw[j] += err * row[j]
            gb += err
        for j in range(n_feat):
            w[j] -= lr * gw[j] / len(z)
        b -= lr * gb / len(z)
    return w  # 표준화 좌표계의 계수 — 부호와 상대 크기가 의미


def implied_multipliers(coef: list[float]) -> dict[str, float]:
    """계수 → '그 특징이 1σ 높은 간선을 얼마나 싸게 보는가'(exp(−β)). 1보다 작으면 선호."""
    return {name: round(math.exp(-c), 3) for name, c in zip(FEATURES, coef, strict=True)}


# ── 합성 검증 ───────────────────────────────────────────────────────────────


def synthetic_walks(
    seed: int = 1, n: int = 40
) -> tuple[list[dict[str, Any]], list[RouteEdge], dict]:
    """합성 세계에서 '그늘 거리를 선호하는' 가상 사용자의 walks를 만든다."""
    from gildle.scripts.verify_pipeline_synthetic import _node, analytic_noon_lookup, build_world

    world = build_world()
    shade = analytic_noon_lookup(world)
    adapter = DijkstraRouteGraphAdapter()
    graph = adapter.build_graph(world.edges)
    lookup = {}
    coords: dict[str, Coordinate] = {}
    for e in world.edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e
        if e.from_coord:
            coords[e.from_node] = e.from_coord
        if e.to_coord:
            coords[e.to_node] = e.to_coord
    rng = random.Random(seed)
    walks = []
    for _ in range(n):
        c1, c2 = rng.sample(range(5), 2)
        s, t = _node(0, c1), _node(0, c2)
        # 가상 사용자: 햇빛 간선을 3배 비싸게 느낀다(= 우리가 학습으로 되찾으려는 선호)
        path = adapter.find_shortest_path(
            graph,
            s,
            t,
            lambda e: (
                e.base_distance_m * (1.0 + 2.0 * (1.0 - shade.get((e.from_node, e.to_node), 0.0)))
            ),
        )
        pts = []
        for i in range(len(path) - 1):
            e = lookup[(path[i], path[i + 1])]
            pts.append([e.midpoint.latitude, e.midpoint.longitude])
        walks.append({"path": pts, "season_mode": "summer"})
    return walks, world.edges, shade


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--walks", type=Path)
    args = ap.parse_args()

    if args.synthetic:
        walks, edges, shade = synthetic_walks()
    elif args.walks:
        walks = json.loads(args.walks.read_text(encoding="utf-8"))
        raise SystemExit(
            "실데이터 경로는 walks 기록이 쌓인 뒤 연결한다(scored_edges + 슬롯별 그늘 lookup 필요)"
        )
    else:
        ap.error("--synthetic 또는 --walks 필요")

    examples = build_examples(walks, edges, shade)
    pos = sum(y for _, y in examples)
    coef = fit_logistic(examples)
    mult = implied_multipliers(coef)
    print(
        f"[data] walks {len(walks)} → 예시 {len(examples)} (양성 {pos} / 음성 {len(examples) - pos})"
    )
    print("[coef 표준화]", {n: round(c, 3) for n, c in zip(FEATURES, coef, strict=True)})
    print("[환산 배율 exp(−β)]", mult, "← shade < 1 이면 그늘 선호를 되찾은 것")
    print(
        json.dumps(
            {
                "examples": len(examples),
                "coef": dict(zip(FEATURES, [round(c, 4) for c in coef], strict=True)),
            }
        )
    )


if __name__ == "__main__":
    main()
