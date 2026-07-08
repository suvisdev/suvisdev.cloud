import pytest

from gildle.adapter.inbound.api.schemas.route_schema import RouteRequestSchema
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.season_mode import SeasonMode


class TestRouteRequestSchemaToDomain:
    def test_converts_to_domain_value_objects(self):
        schema = RouteRequestSchema(
            start_lat=37.5260,
            start_lng=126.9245,
            end_lat=37.5270,
            end_lng=126.9290,
            mode="spring_autumn",
        )

        start, end, mode = schema.to_domain()

        assert start == Coordinate(latitude=37.5260, longitude=126.9245)
        assert end == Coordinate(latitude=37.5270, longitude=126.9290)
        assert mode is SeasonMode.SPRING_AUTUMN

    def test_invalid_mode_raises_value_error(self):
        schema = RouteRequestSchema(
            start_lat=37.5, start_lng=127.0, end_lat=37.5, end_lng=127.0, mode="summer"
        )
        with pytest.raises(ValueError):
            schema.to_domain()
