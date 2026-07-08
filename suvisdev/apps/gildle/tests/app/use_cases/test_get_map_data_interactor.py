from tests.app.fakes import FakeHazardZoneRepository, FakeTreeSegmentRepository

from gildle.app.use_cases.get_map_data_interactor import (
    GetMapVisualizationDataInteractor,
)
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.season_mode import SeasonMode
from gildle.domain.value_objects.tree_species import TreeSpecies


def _segment() -> TreeSegment:
    return TreeSegment(
        id=1,
        road_name="여의대로",
        start=Coordinate(latitude=37.50, longitude=127.00),
        end=Coordinate(latitude=37.52, longitude=127.04),
        species=TreeSpecies.CHERRY,
        quantity=120,
        managing_agency="영등포구청",
    )


def _hazard() -> HazardZone:
    return HazardZone(
        id=9,
        center=Coordinate(latitude=37.51, longitude=127.02),
        radius_meters=200.0,
        accident_count=5,
        description="결빙 다발 교차로",
    )


def _interactor(segments=None, hazards=None):
    return GetMapVisualizationDataInteractor(
        tree_repository=FakeTreeSegmentRepository(segments),
        hazard_repository=FakeHazardZoneRepository(hazards),
    )


class TestGetMapDataSpringAutumn:
    def test_spring_mode_returns_tree_segments_and_no_hazards(self):
        interactor = _interactor(segments=[_segment()], hazards=[_hazard()])

        data = interactor.execute(SeasonMode.SPRING_AUTUMN)

        assert data["mode"] == "spring_autumn"
        assert len(data["tree_segments"]) == 1
        assert data["hazard_zones"] == []
        tree = data["tree_segments"][0]
        assert tree["species"] == "벚나무"
        assert tree["start"] == {"latitude": 37.50, "longitude": 127.00}


class TestGetMapDataWinterSafety:
    def test_winter_mode_returns_hazards_and_no_tree_segments(self):
        interactor = _interactor(segments=[_segment()], hazards=[_hazard()])

        data = interactor.execute(SeasonMode.WINTER_SAFETY)

        assert data["mode"] == "winter_safety"
        assert data["tree_segments"] == []
        assert len(data["hazard_zones"]) == 1
        zone = data["hazard_zones"][0]
        assert zone["radius_meters"] == 200.0
        assert zone["center"] == {"latitude": 37.51, "longitude": 127.02}
