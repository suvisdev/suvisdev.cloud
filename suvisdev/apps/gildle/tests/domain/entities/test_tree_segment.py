from types import SimpleNamespace

import pytest

from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies


def _segment(**overrides) -> TreeSegment:
    base = dict(
        id=1,
        road_name="여의대로",
        start=Coordinate(latitude=37.50, longitude=127.00),
        end=Coordinate(latitude=37.52, longitude=127.04),
        species=TreeSpecies.CHERRY,
        quantity=120,
        managing_agency="영등포구청",
    )
    base.update(overrides)
    return TreeSegment(**base)


class TestTreeSegment:
    def test_creates_with_all_fields(self):
        seg = _segment()
        assert seg.id == 1
        assert seg.road_name == "여의대로"
        assert seg.species is TreeSpecies.CHERRY
        assert seg.quantity == 120
        assert seg.managing_agency == "영등포구청"

    def test_midpoint_is_average_of_start_and_end(self):
        seg = _segment(
            start=Coordinate(latitude=37.50, longitude=127.00),
            end=Coordinate(latitude=37.52, longitude=127.04),
        )
        mid = seg.midpoint()
        assert mid.latitude == pytest.approx(37.51)
        assert mid.longitude == pytest.approx(127.02)


class TestTreeSegmentFromOrm:
    def test_from_orm_maps_columns_to_domain(self):
        orm = SimpleNamespace(
            id=7,
            road_name="국회대로",
            start_latitude=37.531,
            start_longitude=126.914,
            end_latitude=37.533,
            end_longitude=126.918,
            species="느티나무",
            quantity=45,
            managing_agency="영등포구청",
        )
        seg = TreeSegment.from_orm(orm)
        assert seg.id == 7
        assert seg.road_name == "국회대로"
        assert seg.start == Coordinate(latitude=37.531, longitude=126.914)
        assert seg.end == Coordinate(latitude=37.533, longitude=126.918)
        assert seg.species is TreeSpecies.ZELKOVA
        assert seg.quantity == 45
