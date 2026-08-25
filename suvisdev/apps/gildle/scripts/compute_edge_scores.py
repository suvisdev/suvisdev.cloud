"""route_edge 원천 점수(tree/hazard/dog_friendly) 배치 산정.

독립 실행: python -m gildle.scripts.compute_edge_scores
멱등: 여러 번 돌려도 결과 동일.
어댑터 레이어 — 도메인 객체를 사용하되 도메인을 수정하지 않는다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path

from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

logger = logging.getLogger(__name__)

_PROXIMITY_MATCH_M = 50.0
_DENSITY_CAP = 200.0
_DOG_FRIENDLY_TREE_WEIGHT = 0.7
_DOG_FRIENDLY_BASE = 0.3


class EdgeScoreCalculator:
    """route_edge의 원천 점수를 산정하는 배치 서비스.

    RouteWeightCalculator(계절별 가중치)와 역할이 다르다:
    - 이 클래스: 원천 점수 산정 (0~1, 정적)
    - RouteWeightCalculator: 모드별 가중치 적용 (런타임)
    """

    def compute_tree_score(
        self,
        edge: RouteEdge,
        segments: list[TreeSegment],
    ) -> float:
        matched = self._match_segments(edge, segments)
        if not matched:
            return 0.0

        total_qty = sum(s.quantity for s in matched)
        bonus_qty = sum(s.quantity for s in matched if s.species.is_bonus_species)

        if total_qty == 0:
            bonus_count = sum(1 for s in matched if s.species.is_bonus_species)
            bonus_ratio = bonus_count / len(matched)
            density = 0.0
        else:
            bonus_ratio = bonus_qty / total_qty
            density = min(1.0, total_qty / _DENSITY_CAP)

        return min(1.0, bonus_ratio * 0.6 + density * 0.4)

    def compute_hazard_score(
        self,
        edge: RouteEdge,
        hazards: list[HazardZone],
    ) -> float:
        max_score = 0.0
        for hazard in hazards:
            distance = edge.midpoint.distance_to(hazard.center)
            if distance <= hazard.radius_meters:
                if hazard.radius_meters == 0:
                    score = 1.0
                else:
                    score = 1.0 - (distance / hazard.radius_meters)
                max_score = max(max_score, score)
        return min(1.0, max_score)

    def compute_dog_friendly_score(self, tree_score: float) -> float:
        return min(1.0, tree_score * _DOG_FRIENDLY_TREE_WEIGHT + _DOG_FRIENDLY_BASE)

    def score_edges(
        self,
        edges: list[RouteEdge],
        segments: list[TreeSegment],
        hazards: list[HazardZone],
    ) -> list[RouteEdge]:
        scored: list[RouteEdge] = []
        for edge in edges:
            ts = self.compute_tree_score(edge, segments)
            hs = self.compute_hazard_score(edge, hazards)
            ds = self.compute_dog_friendly_score(ts)
            scored.append(
                replace(edge, tree_score=ts, hazard_score=hs, dog_friendly_score=ds)
            )
        return scored

    def _match_segments(
        self, edge: RouteEdge, segments: list[TreeSegment]
    ) -> list[TreeSegment]:
        if edge.road_name is not None:
            by_name = [s for s in segments if s.road_name == edge.road_name]
            if by_name:
                return by_name

        return [
            s
            for s in segments
            if edge.midpoint.distance_to(s.midpoint()) <= _PROXIMITY_MATCH_M
        ]


def save_scored_edges(edges: list[RouteEdge], path: Path) -> None:
    records = []
    for e in edges:
        rec: dict[str, object] = {
            "from_node": e.from_node,
            "to_node": e.to_node,
            "base_distance_m": e.base_distance_m,
            "midpoint_lat": e.midpoint.latitude,
            "midpoint_lng": e.midpoint.longitude,
            "road_name": e.road_name,
            "tree_score": round(e.tree_score, 6),
            "hazard_score": round(e.hazard_score, 6),
            "dog_friendly_score": round(e.dog_friendly_score, 6),
        }
        if e.from_coord is not None:
            rec["from_lat"] = e.from_coord.latitude
            rec["from_lng"] = e.from_coord.longitude
        if e.to_coord is not None:
            rec["to_lat"] = e.to_coord.latitude
            rec["to_lng"] = e.to_coord.longitude
        records.append(rec)
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def load_scored_edges(path: Path) -> list[RouteEdge]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [
        RouteEdge(
            from_node=r["from_node"],
            to_node=r["to_node"],
            base_distance_m=r["base_distance_m"],
            midpoint=Coordinate(latitude=r["midpoint_lat"], longitude=r["midpoint_lng"]),
            road_name=r["road_name"],
            tree_score=r["tree_score"],
            hazard_score=r["hazard_score"],
            dog_friendly_score=r["dog_friendly_score"],
        )
        for r in records
    ]


def main() -> None:
    import os
    from gildle.dependencies.route_provider import (
        _csv_encoding,
        _hazard_csv_path,
        _tree_csv_path,
    )
    from gildle.adapter.outbound.repositories.csv_tree_segment_repository import (
        CsvTreeSegmentRepository,
    )
    from gildle.adapter.outbound.repositories.traffic_authority_hazard_zone_repository import (
        TrafficAuthorityHazardZoneRepository,
    )
    from gildle.adapter.outbound.graph.sample_walk_graph_source import (
        SampleWalkGraphSource,
    )

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data_dir = Path(__file__).resolve().parent.parent / "data"
    walk_graph_path = Path(
        os.getenv("GILDLE_WALK_GRAPH", str(data_dir / "sample_walk_graph.json"))
    )
    output_path = Path(
        os.getenv("GILDLE_SCORED_EDGES", str(data_dir / "scored_edges.json"))
    )

    encoding = _csv_encoding()
    segments = CsvTreeSegmentRepository(
        csv_path=_tree_csv_path(), encoding=encoding
    ).find_all()
    hazards = TrafficAuthorityHazardZoneRepository(
        csv_path=_hazard_csv_path(), encoding=encoding
    ).find_all()
    edges = SampleWalkGraphSource(json_path=walk_graph_path).load_edges("")

    logger.info("edges=%d  segments=%d  hazards=%d", len(edges), len(segments), len(hazards))

    calc = EdgeScoreCalculator()
    scored = calc.score_edges(edges, segments, hazards)

    save_scored_edges(scored, output_path)
    logger.info("저장: %s (%d edges)", output_path, len(scored))

    nonzero_tree = sum(1 for e in scored if e.tree_score > 0)
    nonzero_hazard = sum(1 for e in scored if e.hazard_score > 0)
    logger.info("tree_score>0: %d  hazard_score>0: %d", nonzero_tree, nonzero_hazard)


if __name__ == "__main__":
    main()
