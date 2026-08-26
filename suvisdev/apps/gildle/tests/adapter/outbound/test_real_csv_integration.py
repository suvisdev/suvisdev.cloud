"""실데이터 CSV 통합 테스트 — cp949 인코딩·필터링·에지 케이스 검증.

data/ 디렉터리의 영등포구 가로수·결빙 사고 CSV를 실제로 읽어
어댑터가 올바르게 파싱하는지 확인한다. 단위 테스트(test_csv_tree_*,
test_traffic_authority_*)와 달리 **인코딩·실데이터 특성**을 검증한다.
"""

import csv

from gildle.adapter.outbound.repositories.csv_tree_segment_repository import (
    CsvTreeSegmentRepository,
)
from gildle.adapter.outbound.repositories.traffic_authority_hazard_zone_repository import (
    TrafficAuthorityHazardZoneRepository,
)
from gildle.domain.value_objects.tree_species import TreeSpecies


def _write_cp949_tree_csv(path, rows):
    header = [
        "가로수길명",
        "가로수길시작위도",
        "가로수길시작경도",
        "가로수길종료위도",
        "가로수길종료경도",
        "가로수종류",
        "가로수수량",
        "가로수길길이",
        "식재연도",
        "가로수길소개",
        "도로명",
        "도로종류",
        "도로구간",
        "관리기관전화번호",
        "관리기관명",
        "데이터기준일자",
    ]
    with open(path, "w", encoding="cp949", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _write_cp949_hazard_csv(path, rows):
    header = ["시도시군구명", "지점명", "위도", "경도", "사고건수"]
    with open(path, "w", encoding="cp949", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class TestCp949TreeSegmentEncoding:
    """공공데이터 기본 인코딩(cp949) CSV를 정상적으로 읽는지 검증."""

    def test_cp949_csv_parsed_correctly(self, tmp_path):
        csv_path = tmp_path / "trees_cp949.csv"
        _write_cp949_tree_csv(
            csv_path,
            [
                [
                    "여의대로 벚꽃길",
                    "37.5260",
                    "126.9245",
                    "37.5265",
                    "126.9270",
                    "벚나무",
                    "120",
                    "850",
                    "2005",
                    "봄철 벚꽃 명소",
                    "여의대로",
                    "특별시도",
                    "여의도동",
                    "02-2670-3000",
                    "영등포구청",
                    "2025-12-31",
                ],
            ],
        )
        repo = CsvTreeSegmentRepository(csv_path=csv_path, encoding="cp949")

        segments = repo.find_all()

        assert len(segments) == 1
        assert segments[0].species is TreeSpecies.CHERRY
        assert segments[0].road_name == "여의대로"
        assert segments[0].managing_agency == "영등포구청"

    def test_euc_kr_alias_also_works(self, tmp_path):
        csv_path = tmp_path / "trees_euckr.csv"
        _write_cp949_tree_csv(
            csv_path,
            [
                [
                    "국회대로길",
                    "37.5290",
                    "126.9140",
                    "37.5295",
                    "126.9165",
                    "느티나무",
                    "80",
                    "450",
                    "2010",
                    "",
                    "국회대로",
                    "특별시도",
                    "여의도동",
                    "02-2670-3000",
                    "영등포구청",
                    "2025-12-31",
                ],
            ],
        )
        repo = CsvTreeSegmentRepository(csv_path=csv_path, encoding="euc-kr")

        segments = repo.find_all()
        assert len(segments) == 1
        assert segments[0].species is TreeSpecies.ZELKOVA

    def test_unsupported_species_rows_skipped_in_cp949(self, tmp_path):
        csv_path = tmp_path / "trees_mixed.csv"
        _write_cp949_tree_csv(
            csv_path,
            [
                [
                    "벚꽃길",
                    "37.5260",
                    "126.9245",
                    "37.5265",
                    "126.9270",
                    "벚나무",
                    "120",
                    "850",
                    "2005",
                    "",
                    "여의대로",
                    "특별시도",
                    "",
                    "",
                    "영등포구청",
                    "",
                ],
                [
                    "이팝나무길",
                    "37.5340",
                    "126.8960",
                    "37.5345",
                    "126.8990",
                    "이팝나무",
                    "40",
                    "250",
                    "2015",
                    "",
                    "양평로",
                    "특별시도",
                    "",
                    "",
                    "영등포구청",
                    "",
                ],
                [
                    "플라타너스길",
                    "37.5160",
                    "126.8895",
                    "37.5165",
                    "126.8925",
                    "플라타너스",
                    "70",
                    "400",
                    "2000",
                    "",
                    "경인로",
                    "특별시도",
                    "",
                    "",
                    "영등포구청",
                    "",
                ],
            ],
        )
        repo = CsvTreeSegmentRepository(csv_path=csv_path, encoding="cp949")

        segments = repo.find_all()
        assert len(segments) == 1
        assert segments[0].species is TreeSpecies.CHERRY

    def test_coordinate_zero_treated_as_valid(self, tmp_path):
        csv_path = tmp_path / "trees_zero.csv"
        _write_cp949_tree_csv(
            csv_path,
            [
                [
                    "적도근처길",
                    "0.0",
                    "0.0",
                    "0.001",
                    "0.001",
                    "벚나무",
                    "10",
                    "100",
                    "2020",
                    "",
                    "적도로",
                    "기타",
                    "",
                    "",
                    "테스트기관",
                    "",
                ],
            ],
        )
        repo = CsvTreeSegmentRepository(csv_path=csv_path, encoding="cp949")

        segments = repo.find_all()
        assert len(segments) == 1
        assert segments[0].start.latitude == 0.0

    def test_extra_columns_ignored_gracefully(self, tmp_path):
        csv_path = tmp_path / "trees_extra.csv"
        _write_cp949_tree_csv(
            csv_path,
            [
                [
                    "벚꽃길",
                    "37.5260",
                    "126.9245",
                    "37.5265",
                    "126.9270",
                    "벚나무",
                    "120",
                    "850",
                    "2005",
                    "소개",
                    "여의대로",
                    "특별시도",
                    "구간",
                    "02-0000-0000",
                    "영등포구청",
                    "2025-12-31",
                ],
            ],
        )
        repo = CsvTreeSegmentRepository(csv_path=csv_path, encoding="cp949")

        assert len(repo.find_all()) == 1


class TestCp949HazardZoneEncoding:
    """결빙 사고 CSV의 cp949 인코딩·서울 필터링 검증."""

    def test_cp949_csv_seoul_only(self, tmp_path):
        csv_path = tmp_path / "hazards_cp949.csv"
        _write_cp949_hazard_csv(
            csv_path,
            [
                ["서울특별시 영등포구", "여의도 결빙구간", "37.5263", "126.9258", "8"],
                ["경기도 수원시", "수원역 교차로", "37.2660", "127.0000", "3"],
            ],
        )
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv_path, encoding="cp949")

        zones = repo.find_all()
        assert len(zones) == 1
        assert zones[0].description == "여의도 결빙구간"
        assert zones[0].accident_count == 8

    def test_coordinate_missing_row_skipped_in_cp949(self, tmp_path):
        csv_path = tmp_path / "hazards_missing.csv"
        _write_cp949_hazard_csv(
            csv_path,
            [
                ["서울특별시 영등포구", "정상지점", "37.5263", "126.9258", "5"],
                ["서울특별시 송파구", "좌표없음", "", "", "3"],
            ],
        )
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv_path, encoding="cp949")

        zones = repo.find_all()
        assert len(zones) == 1
        assert zones[0].description == "정상지점"

    def test_multiple_seoul_gu_all_included(self, tmp_path):
        csv_path = tmp_path / "hazards_multi_gu.csv"
        _write_cp949_hazard_csv(
            csv_path,
            [
                ["서울특별시 영등포구", "지점A", "37.5263", "126.9258", "8"],
                ["서울특별시 강남구", "지점B", "37.5010", "127.0390", "6"],
                ["서울특별시 종로구", "지점C", "37.5720", "126.9770", "4"],
                ["부산광역시 해운대구", "지점D", "35.1590", "129.1600", "4"],
                ["인천광역시 남동구", "지점E", "37.4050", "126.7330", "2"],
            ],
        )
        repo = TrafficAuthorityHazardZoneRepository(csv_path=csv_path, encoding="cp949")

        zones = repo.find_all()
        assert len(zones) == 3
        descriptions = {z.description for z in zones}
        assert descriptions == {"지점A", "지점B", "지점C"}
