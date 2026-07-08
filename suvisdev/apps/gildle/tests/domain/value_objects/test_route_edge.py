from dataclasses import FrozenInstanceError

import pytest

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class TestRouteEdge:
    def test_creates_with_all_fields(self):
        mid = Coordinate(latitude=37.5, longitude=127.0)
        edge = RouteEdge(
            from_node="A",
            to_node="B",
            base_distance_m=120.0,
            midpoint=mid,
            road_name="여의대로",
        )
        assert edge.from_node == "A"
        assert edge.to_node == "B"
        assert edge.base_distance_m == 120.0
        assert edge.midpoint == mid
        assert edge.road_name == "여의대로"

    def test_road_name_is_optional(self):
        edge = RouteEdge(
            from_node="A",
            to_node="B",
            base_distance_m=10.0,
            midpoint=Coordinate(latitude=0.0, longitude=0.0),
            road_name=None,
        )
        assert edge.road_name is None

    def test_is_frozen(self):
        edge = RouteEdge(
            from_node="A",
            to_node="B",
            base_distance_m=10.0,
            midpoint=Coordinate(latitude=0.0, longitude=0.0),
            road_name=None,
        )
        with pytest.raises(FrozenInstanceError):
            edge.base_distance_m = 20.0  # type: ignore[misc]
