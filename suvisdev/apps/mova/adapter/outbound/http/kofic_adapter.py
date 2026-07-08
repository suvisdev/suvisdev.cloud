"""KOFIC(KOBIS) Open API 클라이언트."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

KOFIC_BASE = "http://www.kobis.or.kr/kobisopenapi/webservice/rest"


class KoficAdapterError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class KoficAdapter:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()
        if not self.api_key:
            raise KoficAdapterError(
                "KOFIC_API_KEY가 없습니다. suvisdev/.env 에 키를 설정하세요.",
                status_code=503,
            )

    async def _get(self, path: str, *, params: dict[str, str]) -> dict:
        query = {"key": self.api_key, **params}
        url = f"{KOFIC_BASE}{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=query)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise KoficAdapterError(
                f"KOFIC HTTP {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise KoficAdapterError(f"KOFIC 연결 실패: {e!s}") from e

    async def fetch_daily_boxoffice(self, target_date: str) -> list[dict]:
        data = await self._get(
            "/boxoffice/searchDailyBoxOfficeList.json",
            params={"targetDt": target_date},
        )
        box_office_result = data.get("boxOfficeResult") or {}
        return list(box_office_result.get("dailyBoxOfficeList") or [])

    async def fetch_weekly_boxoffice(self, target_date: str, *, week_gb: str = "0") -> list[dict]:
        data = await self._get(
            "/boxoffice/searchWeeklyBoxOfficeList.json",
            params={"targetDt": target_date, "weekGb": week_gb},
        )
        box_office_result = data.get("boxOfficeResult") or {}
        return list(box_office_result.get("weeklyBoxOfficeList") or [])

    async def fetch_movie_info(self, movie_cd: str) -> dict:
        data = await self._get(
            "/movie/searchMovieInfo.json",
            params={"movieCd": movie_cd},
        )
        movie_info_result = data.get("movieInfoResult") or {}
        return dict(movie_info_result.get("movieInfo") or {})

    @staticmethod
    def default_target_date() -> str:
        return (date.today() - timedelta(days=1)).strftime("%Y%m%d")
