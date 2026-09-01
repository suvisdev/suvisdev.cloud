"""TMDB(The Movie Database) v3 API 클라이언트."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# 429(rate limit) 재시도 횟수·기본 백오프(초) — Retry-After 헤더가 있으면 그걸 우선한다.
_RATE_LIMIT_MAX_RETRIES = 3
_RATE_LIMIT_BACKOFF_SECONDS = 1.0


def build_image_url(path: str | None) -> str:
    """TMDB 이미지 경로(poster_path/profile_path 공용) → 절대 URL."""
    if not path:
        return ""
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{TMDB_IMAGE_BASE}{normalized}"


def _rate_limit_wait_seconds(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return _RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1)


class TmdbAdapterError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class TmdbAdapter:
    def __init__(self, api_key: str, *, language: str = "ko-KR") -> None:
        self.api_key = api_key.strip()
        self.language = language
        if not self.api_key:
            raise TmdbAdapterError(
                "TMDB_API_KEY가 없습니다. suvisdev/.env 에 키를 설정하세요.",
                status_code=503,
            )

    def poster_url(self, poster_path: str | None) -> str:
        return build_image_url(poster_path)

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = {"api_key": self.api_key, "language": self.language}
        if params:
            query.update(params)
        url = f"{TMDB_BASE}{path}"
        for attempt in range(_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.get(url, params=query)
                    response.raise_for_status()
                    result: dict[str, Any] = response.json()
                    return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < _RATE_LIMIT_MAX_RETRIES:
                    wait = _rate_limit_wait_seconds(e.response, attempt)
                    logger.warning(
                        "[TmdbAdapter] %s 429 rate limit, %.1fs 후 재시도(%d/%d)",
                        path,
                        wait,
                        attempt + 1,
                        _RATE_LIMIT_MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue
                detail = ""
                try:
                    detail = e.response.json().get("status_message", "")
                except Exception:
                    pass
                msg = detail or f"TMDB HTTP {e.response.status_code}"
                logger.warning("[TmdbAdapter] %s %s — %s", path, e.response.status_code, msg)
                raise TmdbAdapterError(msg, status_code=e.response.status_code) from e
            except httpx.RequestError as e:
                raise TmdbAdapterError(f"TMDB 연결 실패: {e!s}") from e
        msg = "TMDB 429 rate limit — 재시도 초과"
        raise TmdbAdapterError(msg, status_code=429)

    async def genre_map(self) -> dict[int, str]:
        data = await self._get("/genre/movie/list")
        return {int(g["id"]): str(g["name"]) for g in data.get("genres", []) if g.get("id")}

    async def fetch_popular(self, *, page: int = 1) -> list[dict[str, Any]]:
        data = await self._get("/movie/popular", params={"page": max(1, page)})
        return list(data.get("results") or [])

    async def fetch_top_rated(self, *, page: int = 1) -> list[dict[str, Any]]:
        data = await self._get("/movie/top_rated", params={"page": max(1, page)})
        return list(data.get("results") or [])

    async def fetch_upcoming(
        self, *, page: int = 1, region: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": max(1, page)}
        if region:
            params["region"] = region
        data = await self._get("/movie/upcoming", params=params)
        return list(data.get("results") or [])

    async def fetch_discover(
        self,
        *,
        page: int = 1,
        with_origin_country: str | None = None,
        with_genres: str | None = None,
        with_keywords: str | None = None,
        sort_by: str = "popularity.desc",
        include_adult: bool = False,
        vote_count_gte: int | None = None,
        region: str | None = None,
        with_release_type: str | None = None,
        release_date_lte: str | None = None,
    ) -> list[dict[str, Any]]:
        """TMDB /discover/movie — region/genre 등 필터를 걸어 대량 수집할 때 사용.

        `include_adult`는 기본 False(성인 영화 제외). `vote_count_gte`로 최소
        투표 수 필터를 걸면 무명·저품질 영화(19금 성인물 다수 포함)를 배제할
        수 있음 — 2026-08-14 사용자 지적("이상한 19금영화 말고").
        """
        params: dict[str, Any] = {
            "page": max(1, page),
            "sort_by": sort_by,
            "include_adult": "true" if include_adult else "false",
        }
        if with_origin_country:
            params["with_origin_country"] = with_origin_country
        if with_genres:
            params["with_genres"] = with_genres
        if with_keywords:
            params["with_keywords"] = with_keywords
        if vote_count_gte is not None:
            params["vote_count.gte"] = int(vote_count_gte)
        # region+with_release_type을 함께 주면 release_date.* 필터가 그 나라의
        # 개봉일 기준으로 동작한다 — "한국에 개봉한 영화"(외화 포함) 수집용.
        if region:
            params["region"] = region
        if with_release_type:
            params["with_release_type"] = with_release_type
        if release_date_lte:
            params["release_date.lte"] = release_date_lte
        data = await self._get("/discover/movie", params=params)
        return list(data.get("results") or [])

    async def search_movies(self, query: str, *, page: int = 1) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            return []
        data = await self._get("/search/movie", params={"query": q, "page": max(1, page)})
        return list(data.get("results") or [])

    async def fetch_movie_reviews(self, tmdb_id: int, *, page: int = 1) -> list[dict[str, Any]]:
        """TMDB 리뷰 목록. 리뷰는 언어별 저장이라 ko-KR엔 거의 없어 en-US로 조회
        (evaluate 트랙에서 LLM이 한국어로 요약한다, 2026-08-28)."""
        data = await self._get(
            f"/movie/{tmdb_id}/reviews", params={"language": "en-US", "page": page}
        )
        return list(data.get("results") or [])

    async def fetch_movie_vote_count(self, tmdb_id: int) -> int:
        """vote_count만 필요할 때의 경량 조회 — append_to_response 없는 기본 상세."""
        data = await self._get(f"/movie/{int(tmdb_id)}")
        return int(data.get("vote_count") or 0)

    async def fetch_movie_keywords(self, tmdb_id: int) -> list[str]:
        """TMDB 키워드 이름 목록(영어 소문자) — 키워드 태그 백필용."""
        data = await self._get(f"/movie/{int(tmdb_id)}/keywords")
        return [str(k["name"]).strip().lower() for k in data.get("keywords") or [] if k.get("name")]

    async def fetch_movie_detail(self, tmdb_id: int) -> dict[str, Any]:
        return await self._get(
            f"/movie/{int(tmdb_id)}",
            params={
                "append_to_response": "credits,release_dates,watch/providers,videos",
                # 기본 language(ko-KR)만 걸면 한국어 트레일러가 없는 영화는 videos가
                # 통째로 빈다 — en/영상-언어-없음까지 넓혀 폴백을 확보한다.
                "include_video_language": "ko,en,null",
            },
        )
