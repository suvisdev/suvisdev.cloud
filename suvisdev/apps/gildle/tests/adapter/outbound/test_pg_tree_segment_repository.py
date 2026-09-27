"""PgTreeSegmentRepository 단위 테스트 — SQLite in-memory DB."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import gildle.adapter.outbound.orm.tree_segment_orm  # noqa: F401
from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.tree_segment_orm import TreeSegmentOrm
from gildle.adapter.outbound.pg.tree_segment_pg_repository import (
    PgTreeSegmentRepository,
)
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    GildleBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return factory()


def _cherry_segment() -> TreeSegment:
    return TreeSegment(
        id=None,
        road_name="여의대로",
        start=Coordinate(latitude=37.526, longitude=126.924),
        end=Coordinate(latitude=37.528, longitude=126.928),
        species=TreeSpecies.CHERRY,
        quantity=120,
        managing_agency="영등포구청",
    )


def _zelkova_segment() -> TreeSegment:
    return TreeSegment(
        id=None,
        road_name="국회대로",
        start=Coordinate(latitude=37.529, longitude=126.914),
        end=Coordinate(latitude=37.530, longitude=126.918),
        species=TreeSpecies.ZELKOVA,
        quantity=80,
        managing_agency="영등포구청",
    )


class TestFindAll:
    def test_empty_table_returns_empty_list(self) -> None:
        session = _make_session()
        repo = PgTreeSegmentRepository(session_factory=lambda: session)
        assert repo.find_all() == []

    def test_returns_all_rows_as_entities(self) -> None:
        session = _make_session()
        session.add(
            TreeSegmentOrm(
                road_name="여의대로",
                start_latitude=37.526,
                start_longitude=126.924,
                end_latitude=37.528,
                end_longitude=126.928,
                species="벚나무",
                quantity=120,
                managing_agency="영등포구청",
            )
        )
        session.commit()

        repo = PgTreeSegmentRepository(session_factory=lambda: session)
        result = repo.find_all()

        assert len(result) == 1
        seg = result[0]
        assert seg.road_name == "여의대로"
        assert seg.species == TreeSpecies.CHERRY
        assert seg.quantity == 120
        assert seg.start.latitude == 37.526
        assert seg.end.longitude == 126.928

    def test_from_orm_maps_coordinates_correctly(self) -> None:
        session = _make_session()
        session.add(
            TreeSegmentOrm(
                road_name=None,
                start_latitude=37.500,
                start_longitude=126.900,
                end_latitude=37.510,
                end_longitude=126.910,
                species="느티나무",
                quantity=0,
                managing_agency="",
            )
        )
        session.commit()

        repo = PgTreeSegmentRepository(session_factory=lambda: session)
        seg = repo.find_all()[0]

        assert seg.road_name is None
        assert seg.start.latitude == 37.500
        assert seg.end.latitude == 37.510
        assert seg.species == TreeSpecies.ZELKOVA
