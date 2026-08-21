"""PgHazardZoneRepository 단위 테스트 — SQLite in-memory DB."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import gildle.adapter.outbound.orm.hazard_zone_orm  # noqa: F401
from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.hazard_zone_orm import HazardZoneOrm
from gildle.adapter.outbound.pg.hazard_zone_pg_repository import (
    PgHazardZoneRepository,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    GildleBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return factory()


class TestFindAll:
    def test_empty_table_returns_empty_list(self) -> None:
        session = _make_session()
        repo = PgHazardZoneRepository(session_factory=lambda: session)
        assert repo.find_all() == []

    def test_returns_all_rows_as_entities(self) -> None:
        session = _make_session()
        session.add(
            HazardZoneOrm(
                name="영등포구 여의대로 결빙구간",
                center_latitude=37.526,
                center_longitude=126.925,
                radius_meters=200.0,
                accident_count=5,
            )
        )
        session.add(
            HazardZoneOrm(
                name="마포구 마포대로 결빙구간",
                center_latitude=37.540,
                center_longitude=126.945,
                radius_meters=150.0,
                accident_count=3,
            )
        )
        session.commit()

        repo = PgHazardZoneRepository(session_factory=lambda: session)
        result = repo.find_all()

        assert len(result) == 2

    def test_from_orm_maps_fields_correctly(self) -> None:
        session = _make_session()
        session.add(
            HazardZoneOrm(
                name="강남구 테헤란로 결빙구간",
                center_latitude=37.505,
                center_longitude=127.050,
                radius_meters=180.0,
                accident_count=7,
            )
        )
        session.commit()

        repo = PgHazardZoneRepository(session_factory=lambda: session)
        zone = repo.find_all()[0]

        assert zone.description == "강남구 테헤란로 결빙구간"
        assert zone.center.latitude == 37.505
        assert zone.center.longitude == 127.050
        assert zone.radius_meters == 180.0
        assert zone.accident_count == 7

    def test_contains_check_works_after_load(self) -> None:
        session = _make_session()
        session.add(
            HazardZoneOrm(
                name="테스트",
                center_latitude=37.526,
                center_longitude=126.925,
                radius_meters=200.0,
                accident_count=1,
            )
        )
        session.commit()

        repo = PgHazardZoneRepository(session_factory=lambda: session)
        zone = repo.find_all()[0]

        from gildle.domain.value_objects.coordinate import Coordinate

        near = Coordinate(latitude=37.5265, longitude=126.9255)
        far = Coordinate(latitude=37.600, longitude=127.000)
        assert zone.contains(near)
        assert not zone.contains(far)
