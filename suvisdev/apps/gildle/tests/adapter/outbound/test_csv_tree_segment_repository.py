import pandas as pd

from gildle.adapter.outbound.repositories.csv_tree_segment_repository import (
    CsvTreeSegmentRepository,
)
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _row(**overrides):
    # data.go.kr 전국가로수길정보표준데이터 실제 컬럼명.
    base = {
        "도로명": "여의대로",
        "가로수길시작위도": 37.50,
        "가로수길시작경도": 127.00,
        "가로수길종료위도": 37.52,
        "가로수길종료경도": 127.04,
        "가로수종류": "벚나무",
        "가로수수량": 120,
        "관리기관명": "영등포구청",
    }
    base.update(overrides)
    return base


class TestFindAll:
    def test_each_row_becomes_tree_segment(self, tmp_path):
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(), _row(가로수종류="느티나무", 도로명="국회대로")])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        segments = repo.find_all()

        assert len(segments) == 2
        assert segments[0].species is TreeSpecies.CHERRY
        assert segments[0].start == Coordinate(latitude=37.50, longitude=127.00)
        assert segments[0].road_name == "여의대로"
        assert segments[1].species is TreeSpecies.ZELKOVA


class TestRealDataQuirks:
    """실데이터 특유의 결측치/이상값 처리 — Adapter 경계에서 흡수."""

    def test_unrecognized_species_row_is_skipped(self, tmp_path):
        # 플라타너스/이팝나무 등 보너스 대상이 아닌 수종은 도메인이 모른다 → 제외.
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(), _row(가로수종류="이팝나무")])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        assert len(repo.find_all()) == 1

    def test_missing_coordinate_row_is_skipped(self, tmp_path):
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(), _row(가로수길시작위도="", 가로수길시작경도="")])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        assert len(repo.find_all()) == 1

    def test_out_of_range_coordinate_row_is_skipped(self, tmp_path):
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(), _row(가로수길시작위도=999.0)])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        assert len(repo.find_all()) == 1

    def test_missing_quantity_defaults_to_zero_and_keeps_row(self, tmp_path):
        # 수량 결측은 산책로 매칭에 영향 없으므로 행을 버리지 않고 0으로 둔다.
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(가로수수량="")])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        segments = repo.find_all()
        assert len(segments) == 1
        assert segments[0].quantity == 0

    def test_quantity_with_thousands_comma_is_parsed(self, tmp_path):
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(가로수수량="1,200")])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        assert repo.find_all()[0].quantity == 1200

    def test_missing_road_name_becomes_none(self, tmp_path):
        csv = tmp_path / "trees.csv"
        _write_csv(csv, [_row(도로명="")])
        repo = CsvTreeSegmentRepository(csv_path=csv)

        assert repo.find_all()[0].road_name is None


class TestSaveMany:
    def test_save_many_writes_refined_csv(self, tmp_path):
        refined = tmp_path / "refined_tree_segments.csv"
        repo = CsvTreeSegmentRepository(
            csv_path=tmp_path / "unused.csv", refined_path=refined
        )

        repo.save_many(
            [
                TreeSegment(
                    id=1,
                    road_name="여의대로",
                    start=Coordinate(latitude=37.50, longitude=127.00),
                    end=Coordinate(latitude=37.52, longitude=127.04),
                    species=TreeSpecies.CHERRY,
                    quantity=120,
                    managing_agency="영등포구청",
                )
            ]
        )

        assert refined.exists()
        saved = pd.read_csv(refined)
        assert len(saved) == 1
        assert saved.iloc[0]["road_name"] == "여의대로"
        assert saved.iloc[0]["species"] == "벚나무"
