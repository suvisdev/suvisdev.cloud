from types import SimpleNamespace

from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.value_objects.coordinate import Coordinate


def _zone(**overrides) -> HazardZone:
    base = dict(
        id=1,
        center=Coordinate(latitude=37.50, longitude=127.00),
        radius_meters=200.0,
        accident_count=5,
        description="결빙 다발 교차로",
    )
    base.update(overrides)
    return HazardZone(**base)


class TestHazardZoneContains:
    def test_point_at_center_is_contained(self):
        zone = _zone()
        assert zone.contains(Coordinate(latitude=37.50, longitude=127.00)) is True

    def test_point_within_radius_is_contained(self):
        # 위도 0.0005도 ≈ 55.6m < 200m
        zone = _zone(radius_meters=200.0)
        assert zone.contains(Coordinate(latitude=37.5005, longitude=127.00)) is True

    def test_point_outside_radius_is_not_contained(self):
        # 위도 0.01도 ≈ 1.1km > 200m
        zone = _zone(radius_meters=200.0)
        assert zone.contains(Coordinate(latitude=37.51, longitude=127.00)) is False


class TestHazardZoneFromOrm:
    def test_from_orm_maps_columns_to_domain(self):
        orm = SimpleNamespace(
            id=3,
            name="여의도 결빙 다발지역",
            center_latitude=37.521,
            center_longitude=126.924,
            radius_meters=200.0,
            accident_count=8,
        )
        zone = HazardZone.from_orm(orm)
        assert zone.id == 3
        assert zone.center == Coordinate(latitude=37.521, longitude=126.924)
        assert zone.radius_meters == 200.0
        assert zone.accident_count == 8
        assert zone.description == "여의도 결빙 다발지역"
