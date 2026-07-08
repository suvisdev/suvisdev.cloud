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
    mode: str = Field(..., description="spring_autumn | winter_safety")

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_lat": 37.5260,
                "start_lng": 126.9245,
                "end_lat": 37.5270,
                "end_lng": 126.9290,
                "mode": "spring_autumn",
            }
        }
    }

    def to_domain(self) -> tuple[Coordinate, Coordinate, SeasonMode]:
        """HTTP 스키마를 도메인 값 객체로 변환한다(인바운드 어댑터 책임)."""
        start = Coordinate(latitude=self.start_lat, longitude=self.start_lng)
        end = Coordinate(latitude=self.end_lat, longitude=self.end_lng)
        return start, end, SeasonMode.from_value(self.mode)


class RouteResponseSchema(BaseModel):
    """경로 계산 응답 — 노드 id 경로."""

    path: list[str] = Field(default_factory=list, description="시작→끝 노드 id 경로")
