"""실데이터(scored_edges.json 23만 간선)에서 자체 다익스트라·A*가 networkx와
같은 비용의 경로를 내는지, 방문 노드 수는 얼마나 줄었는지 **모드별로** 잰다
(2026-09-27부터 모드별 휴리스틱 배율 `astar_mode`도 함께).

    python -m gildle.scripts.verify_routing_equivalence [--pairs 200] [--seed 1]

`_docs/GILDLE_ROUTING_ALGORITHM.md` §3-②. 출력 마지막 줄은 JSON 요약.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

from gildle.adapter.outbound.graph.dijkstra_route_graph_adapter import (
    AStarRouteGraphAdapter,
    DijkstraRouteGraphAdapter,
)
from gildle.adapter.outbound.graph.networkx_route_graph_adapter import (
    NetworkXRouteGraphAdapter,
)
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode

_DATA = Path(__file__).resolve().parents[1] / "data" / "scored_edges.json"


def _load_edges_with_coords(path: Path) -> list[RouteEdge]:
    """route_router._load_scored_edges와 같은 필드(노드 좌표 포함 — A* 휴리스틱에 필요).
    compute_edge_scores.load_scored_edges는 좌표를 버려서 쓰지 않는다."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        RouteEdge(
            from_node=r["from_node"],
            to_node=r["to_node"],
            base_distance_m=float(r["base_distance_m"]),
            midpoint=Coordinate(latitude=r["midpoint_lat"], longitude=r["midpoint_lng"]),
            road_name=r.get("road_name"),
            from_coord=Coordinate(latitude=r["from_lat"], longitude=r["from_lng"])
            if "from_lat" in r
            else None,
            to_coord=Coordinate(latitude=r["to_lat"], longitude=r["to_lng"])
            if "to_lat" in r
            else None,
            tree_score=float(r.get("tree_score", 0)),
        )
        for r in rows
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--edges", type=Path, default=_DATA)
    args = ap.parse_args()

    edges = _load_edges_with_coords(args.edges)
    calc = RouteWeightCalculator()

    rng = random.Random(args.seed)
    nodes = sorted({e.from_node for e in edges} | {e.to_node for e in edges})
    pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(args.pairs)]

    lookup: dict[tuple[str, str], RouteEdge] = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e

    impls = {
        "networkx": NetworkXRouteGraphAdapter(),
        "dijkstra": DijkstraRouteGraphAdapter(),
        "astar": AStarRouteGraphAdapter(),
    }
    graphs = {k: v.build_graph(edges) for k, v in impls.items()}

    # 모드별로 잰다 — 가중치 분포(봄가을 0.7~1배, 여름 1~5배)와 휴리스틱 배율이 모드마다
    # 다르다. "astar"는 생성자 기본 0.7, "astar_mode"는 min_multiplier(mode)를 넘긴 것.
    summary: dict[str, Any] = {"pairs": len(pairs), "modes": {}}
    for mode in SeasonMode:
        scale = calc.min_multiplier(mode)

        def weight_fn(e: RouteEdge, mode: SeasonMode = mode) -> float:
            return calc.calculate_edge_weight(e, mode, [], []).value

        def cost(path: list[str]) -> float:
            return sum(weight_fn(lookup[(path[i], path[i + 1])]) for i in range(len(path) - 1))

        runs: dict[str, tuple[Any, dict[str, Any]]] = {
            "networkx": (impls["networkx"], {}),
            "dijkstra": (impls["dijkstra"], {}),
            "astar": (impls["astar"], {}),
            "astar_mode": (impls["astar"], {"heuristic_scale": scale}),
        }
        graph_of = {
            "networkx": "networkx",
            "dijkstra": "dijkstra",
            "astar": "astar",
            "astar_mode": "astar",
        }
        mismatches, reachable = 0, 0
        elapsed = dict.fromkeys(runs, 0.0)
        visited = {k: 0 for k in runs if k != "networkx"}
        for s, t in pairs:
            costs: dict[str, float] = {}
            for k, (impl, kw) in runs.items():
                g = graphs[graph_of[k]]
                t0 = time.perf_counter()
                path = impl.find_shortest_path(g, s, t, weight_fn, **kw)
                elapsed[k] += time.perf_counter() - t0
                costs[k] = cost(path) if path else -1.0
                if k in visited:
                    visited[k] += g.last_visited
            if costs["networkx"] >= 0:
                reachable += 1
            if any(abs(costs[k] - costs["networkx"]) > 1e-6 for k in visited):
                mismatches += 1
                print(f"MISMATCH [{mode.value}] {s}→{t}: {costs}")
        per_mode = {
            "heuristic_scale": scale,
            "reachable": reachable,
            "mismatches": mismatches,
            "sec_per_query": {k: round(v / len(pairs), 4) for k, v in elapsed.items()},
            "visited_ratio_over_dijkstra": {
                k: round(visited[k] / max(1, visited["dijkstra"]), 3)
                for k in ("astar", "astar_mode")
            },
        }
        summary["modes"][mode.value] = per_mode
        print(
            f"[{mode.value}] 도달 {reachable}/{len(pairs)} · 불일치 {mismatches} · "
            f"질의당 {per_mode['sec_per_query']} · 방문 비율 {per_mode['visited_ratio_over_dijkstra']}"
        )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
