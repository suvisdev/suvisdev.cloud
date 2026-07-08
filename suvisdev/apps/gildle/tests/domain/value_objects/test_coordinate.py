from dataclasses import FrozenInstanceError

import pytest

from gildle.domain.value_objects.coordinate import Coordinate


class TestCoordinateValidation:
    def test_valid_coordinate_creates_successfully(self):
        coord = Coordinate(latitude=37.5663, longitude=126.9779)
        assert coord.latitude == 37.5663
        assert coord.longitude == 126.9779

    def test_boundary_values_are_valid(self):
        Coordinate(latitude=-90.0, longitude=-180.0)
        Coordinate(latitude=90.0, longitude=180.0)

    def test_latitude_below_min_raises(self):
        with pytest.raises(ValueError, match="위도"):
            Coordinate(latitude=-90.1, longitude=0.0)

    def test_latitude_above_max_raises(self):
        with pytest.raises(ValueError, match="위도"):
            Coordinate(latitude=90.1, longitude=0.0)

    def test_longitude_below_min_raises(self):
        with pytest.raises(ValueError, match="경도"):
            Coordinate(latitude=0.0, longitude=-180.1)

    def test_longitude_above_max_raises(self):
        with pytest.raises(ValueError, match="경도"):
            Coordinate(latitude=0.0, longitude=180.1)

    def test_is_frozen(self):
        coord = Coordinate(latitude=0.0, longitude=0.0)
        with pytest.raises(FrozenInstanceError):
            coord.latitude = 1.0  # type: ignore[misc]


class TestDistanceTo:
    def test_distance_to_self_is_zero(self):
        coord = Coordinate(latitude=37.5, longitude=127.0)
        assert coord.distance_to(coord) == pytest.approx(0.0, abs=1e-6)

    def test_distance_is_symmetric(self):
        a = Coordinate(latitude=37.5663, longitude=126.9779)
        b = Coordinate(latitude=37.5700, longitude=126.9800)
        assert a.distance_to(b) == pytest.approx(b.distance_to(a))

    def test_one_degree_latitude_is_about_111km(self):
        # 위도 1도 ≈ 111.19km (Haversine, R=6371000)
        a = Coordinate(latitude=0.0, longitude=0.0)
        b = Coordinate(latitude=1.0, longitude=0.0)
        assert a.distance_to(b) == pytest.approx(111195.0, rel=0.001)

    def test_small_distance_in_meters(self):
        # 위도 0.00005도 ≈ 5.56m
        a = Coordinate(latitude=37.5, longitude=127.0)
        b = Coordinate(latitude=37.50005, longitude=127.0)
        assert a.distance_to(b) == pytest.approx(5.56, abs=0.2)
