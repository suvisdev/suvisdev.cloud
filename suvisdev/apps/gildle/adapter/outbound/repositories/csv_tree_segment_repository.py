from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies

# data.go.kr "전국가로수길정보표준데이터"(서울 자치구) 실제 컬럼명.
# 표준데이터셋 스키마 기준. 자치구별 파일 헤더가 다르면 이 상수만 맞추면 된다.
_COL_ROAD_NAME = "도로명"
_COL_START_LAT = "가로수길시작위도"
_COL_START_LNG = "가로수길시작경도"
_COL_END_LAT = "가로수길종료위도"
_COL_END_LNG = "가로수길종료경도"
_COL_SPECIES = "가로수종류"
_COL_QUANTITY = "가로수수량"
_COL_AGENCY = "관리기관명"


def _to_optional_str(value: Any) -> str | None:
    """pandas 값을 정리된 문자열로. 결측(NaN)·빈 문자열은 None."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _to_quantity(value: Any) -> int:
    """수량 파싱. 결측·비정상 값('-', 빈칸, '1,200' 등)은 0으로 처리."""
    if value is None or pd.isna(value):
        return 0
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


class CsvTreeSegmentRepository(TreeSegmentRepository):
    """TreeSegmentRepository의 CSV 구현체(서울 한 자치구 가로수 표준데이터).

    표준데이터는 시작~종료 위경도를 모두 포함하므로 **구간(start~end) 모델**로 적재하며
    Geocoding이 필요 없다. 실데이터 특성상 아래 행은 Adapter 경계에서 걸러 Use Case에는
    깨끗한 엔티티만 넘긴다(예외 처리는 어댑터 책임):
      - 수종을 인식 못 하는 행(플라타너스·이팝나무·혼합표기 등)
      - 시작/종료 좌표가 결측이거나 위경도 범위를 벗어난 행
    수량이 결측/비정상이면 행을 버리지 않고 quantity=0으로 둔다(좌표·수종이 핵심).

    (가정) 자치구 표준데이터에 시작·종료 좌표가 둘 다 있는 자치구(예: 영등포구)를 전제한다.
    단일 좌표만 제공하는 자치구라면 그 파일은 구간 모델이 성립하지 않아 좌표 결측으로 제외된다.
    """

    def __init__(
        self,
        csv_path: str | Path,
        refined_path: str | Path = "refined_tree_segments.csv",
        encoding: str = "utf-8-sig",
    ) -> None:
        self._csv_path = Path(csv_path)
        self._refined_path = Path(refined_path)
        self._encoding = encoding

    def find_all(self) -> list[TreeSegment]:
        frame = pd.read_csv(self._csv_path, encoding=self._encoding)
        segments: list[TreeSegment] = []
        for position, row in enumerate(frame.to_dict("records"), start=1):
            segment = self._to_segment(position, row)
            if segment is not None:
                segments.append(segment)
        return segments

    def save_many(self, segments: list[TreeSegment]) -> None:
        records = [
            {
                "id": s.id,
                "road_name": s.road_name,
                "start_latitude": s.start.latitude,
                "start_longitude": s.start.longitude,
                "end_latitude": s.end.latitude,
                "end_longitude": s.end.longitude,
                "species": s.species.value,
                "quantity": s.quantity,
                "managing_agency": s.managing_agency,
            }
            for s in segments
        ]
        pd.DataFrame(records).to_csv(
            self._refined_path, index=False, encoding=self._encoding
        )

    def _to_segment(self, position: int, row: dict[str, Any]) -> TreeSegment | None:
        try:
            species = TreeSpecies.from_label(str(row[_COL_SPECIES]).strip())
            start = Coordinate(
                latitude=float(row[_COL_START_LAT]),
                longitude=float(row[_COL_START_LNG]),
            )
            end = Coordinate(
                latitude=float(row[_COL_END_LAT]),
                longitude=float(row[_COL_END_LNG]),
            )
        except (ValueError, TypeError, KeyError):
            # 수종 미인식 / 좌표 결측·이상값 → 제외
            return None

        return TreeSegment(
            id=position,
            road_name=_to_optional_str(row.get(_COL_ROAD_NAME)),
            start=start,
            end=end,
            species=species,
            quantity=_to_quantity(row.get(_COL_QUANTITY)),
            managing_agency=_to_optional_str(row.get(_COL_AGENCY)) or "",
        )
