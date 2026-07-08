"""TMDB(The Movie Database) v3 API 클라이언트."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


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
        if not poster_path:
            return ""
        path = poster_path if poster_path.startswith("/") else f"/{poster_path}"
        return f"{TMDB_IMAGE_BASE}{path}"

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict:
        query = {"api_key": self.api_key, "language": self.language}
        if params:
            query.update(params)
        url = f"{TMDB_BASE}{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=query)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
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

    async def genre_map(self) -> dict[int, str]:
        data = await self._get("/genre/movie/list")
        return {int(g["id"]): str(g["name"]) for g in data.get("genres", []) if g.get("id")}

    async def fetch_popular(self, *, page: int = 1) -> list[dict]:
        data = await self._get("/movie/popular", params={"page": max(1, page)})
        return list(data.get("results") or [])

    async def search_movies(self, query: str, *, page: int = 1) -> list[dict]:
        q = query.strip()
        if not q:
            return []
        data = await self._get("/search/movie", params={"query": q, "page": max(1, page)})
        return list(data.get("results") or [])

    async def fetch_movie_detail(self, tmdb_id: int) -> dict:
        return await self._get(
            f"/movie/{int(tmdb_id)}",
            params={"append_to_response": "credits"},
        )
