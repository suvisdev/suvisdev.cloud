"""실데이터(scored_edges.json 23만 간선)에서 자체 다익스트라·A*가 networkx와
같은 비용의 경로를 내는지, 방문 노드 수는 얼마나 줄었는지 잰다.

    python -m gildle.scripts.verify_routing_equivalence [--pairs 200] [--seed 1]

`_docs/GILDLE_ROUTING_ALGORITHM.md` §3-②. 출력 마지막 줄은 JSON 요약.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

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

    # 여름 그늘 모드로 가중치가 거리의 1~5배 사이에서 실제로 흔들리게 한다(tree_score 폴백).
    def weight_fn(e: RouteEdge) -> float:
        return calc.calculate_edge_weight(e, SeasonMode.SUMMER_SHADE, [], []).value

    rng = random.Random(args.seed)
    nodes = sorted({e.from_node for e in edges} | {e.to_node for e in edges})
    pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(args.pairs)]

    lookup: dict[tuple[str, str], RouteEdge] = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e

    def cost(path: list[str]) -> float:
        return sum(weight_fn(lookup[(path[i], path[i + 1])]) for i in range(len(path) - 1))

    impls = {
        "networkx": NetworkXRouteGraphAdapter(),
        "dijkstra": DijkstraRouteGraphAdapter(),
        "astar": AStarRouteGraphAdapter(),
    }
    graphs = {k: v.build_graph(edges) for k, v in impls.items()}

    mismatches, elapsed, visited = 0, {k: 0.0 for k in impls}, {"dijkstra": 0, "astar": 0}
    reachable = 0
    for s, t in pairs:
        costs: dict[str, float] = {}
        for k, impl in impls.items():
            t0 = time.perf_counter()
            path = impl.find_shortest_path(graphs[k], s, t, weight_fn)
            elapsed[k] += time.perf_counter() - t0
            costs[k] = cost(path) if path else -1.0
            if k in visited:
                visited[k] += graphs[k].last_visited
        if costs["networkx"] >= 0:
            reachable += 1
        if any(abs(costs[k] - costs["networkx"]) > 1e-6 for k in ("dijkstra", "astar")):
            mismatches += 1
            print(f"MISMATCH {s}→{t}: {costs}")

    summary = {
        "pairs": len(pairs),
        "reachable": reachable,
        "mismatches": mismatches,
        "sec_per_query": {k: round(v / len(pairs), 4) for k, v in elapsed.items()},
        "visited_ratio_astar_over_dijkstra": round(
            visited["astar"] / max(1, visited["dijkstra"]), 3
        ),
    }
    print(
        f"\n{len(pairs)}쌍 중 도달 {reachable} · 불일치 {mismatches} · "
        f"질의당 {summary['sec_per_query']} · A* 방문 비율 {summary['visited_ratio_astar_over_dijkstra']}"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
