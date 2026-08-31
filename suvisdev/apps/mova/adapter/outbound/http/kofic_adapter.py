"""KOFIC(KOBIS) Open API 클라이언트."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

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

    async def _get(self, path: str, *, params: dict[str, str]) -> dict[str, Any]:
        query = {"key": self.api_key, **params}
        url = f"{KOFIC_BASE}{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=query)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
        except httpx.HTTPStatusError as e:
            raise KoficAdapterError(
                f"KOFIC HTTP {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise KoficAdapterError(f"KOFIC 연결 실패: {e!s}") from e

    async def fetch_daily_boxoffice(self, target_date: str) -> list[dict[str, Any]]:
        data = await self._get(
            "/boxoffice/searchDailyBoxOfficeList.json",
            params={"targetDt": target_date},
        )
        box_office_result = data.get("boxOfficeResult") or {}
        return list(box_office_result.get("dailyBoxOfficeList") or [])

    async def fetch_weekly_boxoffice(
        self, target_date: str, *, week_gb: str = "0"
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "/boxoffice/searchWeeklyBoxOfficeList.json",
            params={"targetDt": target_date, "weekGb": week_gb},
        )
        box_office_result = data.get("boxOfficeResult") or {}
        return list(box_office_result.get("weeklyBoxOfficeList") or [])

    async def fetch_movie_info(self, movie_cd: str) -> dict[str, Any]:
        data = await self._get(
            "/movie/searchMovieInfo.json",
            params={"movieCd": movie_cd},
        )
        movie_info_result = data.get("movieInfoResult") or {}
        return dict(movie_info_result.get("movieInfo") or {})

    async def fetch_movie_list(
        self,
        *,
        page: int = 1,
        item_per_page: int = 100,
        rep_nation_cd: str | None = None,
    ) -> list[dict[str, Any]]:
        """KOFIC 영화 목록 — movieNm/directors/prdtYear/genreAlt 등 기본 필드만 준다(상세는 fetch_movie_info).

        rep_nation_cd: "K"(한국영화)/"F"(외국영화). None이면 국적 필터 없이 전체.
        """
        params: dict[str, str] = {
            "curPage": str(max(1, page)),
            "itemPerPage": str(max(1, min(item_per_page, 100))),
        }
        if rep_nation_cd:
            params["repNationCd"] = rep_nation_cd
        data = await self._get("/movie/searchMovieList.json", params=params)
        movie_list_result = data.get("movieListResult") or {}
        return list(movie_list_result.get("movieList") or [])

    @staticmethod
    def default_target_date() -> str:
        return (date.today() - timedelta(days=1)).strftime("%Y%m%d")
