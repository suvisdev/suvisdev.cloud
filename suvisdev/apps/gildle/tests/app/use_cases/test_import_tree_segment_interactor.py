from tests.app.fakes import FakeGeocodingAdapter

from gildle.app.use_cases.import_tree_segment_interactor import (
    ImportTreeSegmentInteractor,
)
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies


def _row(**overrides) -> dict:
    base = dict(
        road_name="여의대로",
        start_latitude=37.50,
        start_longitude=127.00,
        end_latitude=37.52,
        end_longitude=127.04,
        species="벚나무",
        quantity=120,
        managing_agency="영등포구청",
        address="서울 영등포구 여의대로",
    )
    base.update(overrides)
    return base


class TestImportWithCoordinates:
    def test_row_with_valid_coordinates_becomes_segment(self):
        interactor = ImportTreeSegmentInteractor(geocoder=None)

        segments = interactor.execute([_row()])

        assert len(segments) == 1
        seg = segments[0]
        assert seg.species is TreeSpecies.CHERRY
        assert seg.start == Coordinate(latitude=37.50, longitude=127.00)
        assert seg.end == Coordinate(latitude=37.52, longitude=127.04)
        assert seg.road_name == "여의대로"

    def test_unrecognized_species_is_filtered_out(self):
        interactor = ImportTreeSegmentInteractor(geocoder=None)

        segments = interactor.execute([_row(species="소나무")])

        assert segments == []


class TestImportGeocodingFallback:
    def test_missing_coordinates_uses_geocoder(self):
        geocoder = FakeGeocodingAdapter(
            mapping={"서울 영등포구 국회대로": Coordinate(latitude=37.531, longitude=126.914)}
        )
        interactor = ImportTreeSegmentInteractor(geocoder=geocoder)

        segments = interactor.execute(
            [
                _row(
                    road_name="국회대로",
                    start_latitude=None,
                    start_longitude=None,
                    end_latitude=None,
                    end_longitude=None,
                    address="서울 영등포구 국회대로",
                )
            ]
        )

        assert len(segments) == 1
        # 결측 보완: geocoding 좌표가 시작=종료로 들어간다.
        assert segments[0].start == Coordinate(latitude=37.531, longitude=126.914)
        assert segments[0].end == Coordinate(latitude=37.531, longitude=126.914)
        assert geocoder.calls == ["서울 영등포구 국회대로"]

    def test_missing_coordinates_and_geocoder_fails_is_excluded(self):
        geocoder = FakeGeocodingAdapter(mapping={})  # 항상 None 반환
        interactor = ImportTreeSegmentInteractor(geocoder=geocoder)

        segments = interactor.execute(
            [_row(start_latitude=None, start_longitude=None, address="없는 주소")]
        )

        assert segments == []

    def test_missing_coordinates_without_geocoder_is_excluded(self):
        interactor = ImportTreeSegmentInteractor(geocoder=None)

        segments = interactor.execute([_row(start_latitude=None, start_longitude=None)])

        assert segments == []
