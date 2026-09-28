from __future__ import annotations

from pydantic import BaseModel, Field

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.season_mode import SeasonMode


class RouteRequestSchema(BaseModel):
    """경로 계산 요청 — 시작/끝 좌표 + 계절 모드."""

    start_lat: float = Field(..., description="시작 위도")
    start_lng: float = Field(..., description="시작 경도")
    end_lat: float = Field(..., description="종료 위도")
    end_lng: float = Field(..., description="종료 경도")
    mode: str = Field(..., description="spring_autumn | winter_safety | summer_shade")
    max_detour_ratio: float | None = Field(
        None,
        ge=0.0,
        le=3.0,
        description="지정 시 길이가 최단거리의 (1+비율)배를 넘지 않는 범위에서 모드 선호 반영",
    )
    departure_time: str | None = Field(
        None,
        description='출발 시각 "HH:MM"(KST). summer_shade에서만 사용, 미지정 시 현재 시각.',
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_lat": 37.5260,
                "start_lng": 126.9245,
                "end_lat": 37.5270,
                "end_lng": 126.9290,
                "mode": "summer_shade",
                "departure_time": "14:00",
            }
        }
    }

    def to_domain(self) -> tuple[Coordinate, Coordinate, SeasonMode]:
        """HTTP 스키마를 도메인 값 객체로 변환한다(인바운드 어댑터 책임)."""
        start = Coordinate(latitude=self.start_lat, longitude=self.start_lng)
        end = Coordinate(latitude=self.end_lat, longitude=self.end_lng)
        return start, end, SeasonMode.from_value(self.mode)


class NavigateRequestSchema(BaseModel):
    """노드 ID 기반 경로 탐색 요청."""

    start_node: str = Field(..., description="출발 노드 ID")
    end_node: str = Field(..., description="도착 노드 ID")
    mode: str = Field("spring_autumn", description="spring_autumn | winter_safety | summer_shade")
    max_detour_ratio: float | None = Field(
        None,
        ge=0.0,
        le=3.0,
        description="지정 시 길이가 최단거리의 (1+비율)배를 넘지 않는 범위에서 모드 선호 반영",
    )
    departure_time: str | None = Field(
        None,
        description='출발 시각 "HH:MM"(KST). summer_shade에서만 사용, 미지정 시 현재 시각.',
    )


class LoopRequestSchema(BaseModel):
    """출발 좌표에서 목표 거리만큼 돌아오는 산책 루프 요청."""

    lat: float = Field(..., description="출발 위도")
    lng: float = Field(..., description="출발 경도")
    target_m: float = Field(..., ge=300, le=20_000, description="목표 거리(m)")
    mode: str = Field("spring_autumn", description="spring_autumn | winter_safety | summer_shade")
    departure_time: str | None = Field(None, description='출발 "HH:MM"(여름 그늘 슬롯용)')
    limit: int = Field(3, ge=1, le=6, description="반환 후보 수")


class RouteOptionsRequestSchema(BaseModel):
    """경로 후보 요청 — 빠른·그늘·푸른 길을 나란히(2026-09-28). mode는 '추천' 표시 기준."""

    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    mode: str = Field(
        "spring_autumn",
        description="추천 표시 기준: summer_shade→그늘, spring_autumn→푸른, winter_safety→빠른",
    )
    departure_time: str | None = Field(
        None, description='출발 "HH:MM"(KST). 그늘 계산용, 미지정 시 현재'
    )


class RouteViaRequestSchema(RouteOptionsRequestSchema):
    """고른 장소에 들렀다 가는 경로."""

    via_lat: float
    via_lng: float
    via_name: str = Field(..., max_length=80)
    base_kind: str = Field("fast", pattern="^(fast|shade|green)$")
