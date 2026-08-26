"""CSV 데이터 + scored_edges.json → PostgreSQL 임포트.

독립 실행: python -m gildle.scripts.import_to_db
멱등성: TRUNCATE + INSERT (기존 데이터를 지우고 다시 적재).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from gildle.adapter.outbound.orm.hazard_zone_orm import HazardZoneOrm
from gildle.adapter.outbound.orm.route_edge_orm import RouteEdgeOrm
from gildle.adapter.outbound.orm.route_node_orm import RouteNodeOrm
from gildle.adapter.outbound.orm.tree_segment_orm import TreeSegmentOrm
from gildle.adapter.outbound.repositories.csv_tree_segment_repository import (
    CsvTreeSegmentRepository,
)
from gildle.adapter.outbound.repositories.traffic_authority_hazard_zone_repository import (
    TrafficAuthorityHazardZoneRepository,
)

logger = logging.getLogger(__name__)


def import_tree_segments(session: Session, csv_path: Path, encoding: str = "cp949") -> int:
    csv_repo = CsvTreeSegmentRepository(csv_path=csv_path, encoding=encoding)
    segments = csv_repo.find_all()

    session.query(TreeSegmentOrm).delete()
    for seg in segments:
        session.add(
            TreeSegmentOrm(
                road_name=seg.road_name,
                start_latitude=seg.start.latitude,
                start_longitude=seg.start.longitude,
                end_latitude=seg.end.latitude,
                end_longitude=seg.end.longitude,
                species=seg.species.value,
                quantity=seg.quantity,
                managing_agency=seg.managing_agency,
            )
        )
    session.commit()
    logger.info("tree_segments: %d건 임포트", len(segments))
    return len(segments)


def import_hazard_zones(session: Session, csv_path: Path, encoding: str = "cp949") -> int:
    csv_repo = TrafficAuthorityHazardZoneRepository(csv_path=csv_path, encoding=encoding)
    zones = csv_repo.find_all()

    session.query(HazardZoneOrm).delete()
    for z in zones:
        session.add(
            HazardZoneOrm(
                name=z.description,
                center_latitude=z.center.latitude,
                center_longitude=z.center.longitude,
                radius_meters=z.radius_meters,
                accident_count=z.accident_count,
            )
        )
    session.commit()
    logger.info("hazard_zones: %d건 임포트", len(zones))
    return len(zones)


def import_scored_edges(session: Session, json_path: Path) -> int:
    with open(json_path, encoding="utf-8") as f:
        raw_edges = json.load(f)

    session.query(RouteEdgeOrm).delete()
    session.query(RouteNodeOrm).delete()
    session.commit()

    node_map: dict[str, RouteNodeOrm] = {}
    for raw in raw_edges:
        for node_key in ("from_node", "to_node"):
            osm_id = str(raw[node_key])
            if osm_id not in node_map:
                node = RouteNodeOrm(
                    latitude=raw["midpoint_lat"],
                    longitude=raw["midpoint_lng"],
                    node_type="osm",
                    osm_id=osm_id,
                )
                session.add(node)
                node_map[osm_id] = node

    session.flush()

    for raw in raw_edges:
        from_osm = str(raw["from_node"])
        to_osm = str(raw["to_node"])
        session.add(
            RouteEdgeOrm(
                from_node_id=node_map[from_osm].id,
                to_node_id=node_map[to_osm].id,
                base_distance_m=raw["base_distance_m"],
                road_name=raw.get("road_name"),
                tree_score=raw.get("tree_score", 0.0),
                hazard_score=raw.get("hazard_score", 0.0),
                dog_friendly_score=raw.get("dog_friendly_score", 0.0),
            )
        )
    session.commit()
    logger.info("route_nodes: %d, route_edges: %d건 임포트", len(node_map), len(raw_edges))
    return len(raw_edges)


def main() -> None:
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL 미설정")
        raise SystemExit(1)

    if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(db_url)
    factory = sessionmaker(bind=engine)

    data_dir = Path(__file__).resolve().parent.parent / "data"
    tree_csv = Path(os.getenv("GILDLE_TREE_CSV", str(data_dir / "yeongdeungpo_tree_segments.csv")))
    hazard_csv = Path(os.getenv("GILDLE_HAZARD_CSV", str(data_dir / "icing_accident_zones.csv")))
    scored_json = Path(os.getenv("GILDLE_SCORED_EDGES", str(data_dir / "scored_edges.json")))
    encoding = os.getenv("GILDLE_CSV_ENCODING", "cp949")

    with factory() as session:
        import_tree_segments(session, tree_csv, encoding=encoding)
        import_hazard_zones(session, hazard_csv, encoding=encoding)
        if scored_json.exists():
            import_scored_edges(session, scored_json)
        else:
            logger.warning("scored_edges.json 없음: %s — 건너뜀", scored_json)

    logger.info("임포트 완료")


if __name__ == "__main__":
    main()
