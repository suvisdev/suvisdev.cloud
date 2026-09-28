"""시간표 조회 출력 포트 — booking 트랙 Phase 2 전용."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_chat_dto import CinemaShowtimeDto


class ShowtimePort(ABC):
    @abstractmethod
    async def fetch_showtimes(
        self, cinema_name: str, movie_title: str, *, date: str | None = None
    ) -> CinemaShowtimeDto | None:
        """극장 이름(카카오 로컬 place_name)과 영화 제목으로 시간표를 조회한다.

        date가 None이면 오늘(KST). 조회 실패·미지원 극장이면 None.
        롯데시네마만 지원(Phase 2) — CGV·메가박스는 robots.txt/약관으로 배제.
        """

    async def fetch_nearest_showtimes(
        self,
        lat: float,
        lng: float,
        movie_title: str,
        *,
        date: str | None = None,
        max_km: float = 10.0,
    ) -> CinemaShowtimeDto | None:
        """좌표 기반 최근접 극장 시간표. 구현체가 지원하지 않으면 None."""
        return None

    async def find_showing_cinemas(
        self, area: str, movie_title: str, *, date: str | None = None
    ) -> list[CinemaShowtimeDto]:
        """광역(시·도, 예: "서울") 안에서 이 작품을 상영하는 극장 전부의 시간표.
        가장 이른 회차 순. 구현체가 지원하지 않으면 []."""
        return []

    async def find_showing_cinemas_near(
        self,
        lat: float,
        lng: float,
        movie_title: str,
        *,
        date: str | None = None,
        max_km: float = 5.0,
    ) -> list[CinemaShowtimeDto]:
        """좌표 반경 안의 극장 중 이 작품 상영관 전부(구 단위 요청용). 미지원이면 []."""
        return []
