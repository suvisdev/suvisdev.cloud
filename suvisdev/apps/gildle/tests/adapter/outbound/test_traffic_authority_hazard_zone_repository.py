import pandas as pd

from gildle.adapter.outbound.repositories.traffic_authority_hazard_zone_repository import (
    TrafficAuthorityHazardZoneRepository,
)
from gildle.domain.value_objects.coordinate import Coordinate


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _row(**overrides):
    # 결빙 교통사고 다발지역 실제 컬럼명 (반경 컬럼 없음).
    base = {
        "시도시군구명": "서울특별시 영등포구",
        "지점명": "여의도 결빙 다발지역",
        "위도": 37.521,
        "경도": 126.924,
        "사고건수": 8,
    }
    base.update(overrides)
    return base


class TestFindAll:
    def test_seoul_rows_become_hazard_zones_with_default_radius(self, tmp_path):
        csv = tmp_path / "hazards.csv"
        _write_csv(csv, [_row()])
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv)

        zones = repo.find_all()

        assert len(zones) == 1
        assert zones[0].center == Coordinate(latitude=37.521, longitude=126.924)
        # 반경 컬럼이 없으면 데이터셋 선정기준 200m 기본값.
        assert zones[0].radius_meters == 200.0
        assert zones[0].accident_count == 8
        assert zones[0].description == "여의도 결빙 다발지역"

    def test_non_seoul_rows_are_filtered_out(self, tmp_path):
        csv = tmp_path / "hazards.csv"
        _write_csv(csv, [_row(), _row(시도시군구명="부산광역시 해운대구", 지점명="부산 지점")])
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv)

        zones = repo.find_all()
        assert len(zones) == 1
        assert zones[0].description == "여의도 결빙 다발지역"

    def test_various_seoul_gu_are_kept_by_prefix(self, tmp_path):
        csv = tmp_path / "hazards.csv"
        _write_csv(
            csv,
            [
                _row(시도시군구명="서울특별시 강남구"),
                _row(시도시군구명="서울특별시 종로구"),
            ],
        )
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv)

        assert len(repo.find_all()) == 2


class TestRealDataQuirks:
    def test_radius_column_used_when_present(self, tmp_path):
        csv = tmp_path / "hazards.csv"
        _write_csv(csv, [_row(반경=150.0)])
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv)

        assert repo.find_all()[0].radius_meters == 150.0

    def test_missing_coordinate_row_is_skipped(self, tmp_path):
        csv = tmp_path / "hazards.csv"
        _write_csv(csv, [_row(), _row(위도="", 경도="")])
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv)

        assert len(repo.find_all()) == 1

    def test_missing_accident_count_defaults_to_zero(self, tmp_path):
        csv = tmp_path / "hazards.csv"
        _write_csv(csv, [_row(사고건수="")])
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv)

        assert repo.find_all()[0].accident_count == 0
