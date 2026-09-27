from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MovieImportResultSchema(BaseModel):
    imported: int
    movie_ids: list[int] = Field(default_factory=list)
    rankings_updated: bool = False
    message: str = ""


class TmdbImportRequestSchema(BaseModel):
    tmdb_id: int | None = Field(None, description="TMDB movie id")
    query: str | None = Field(None, description="제목 검색어")
    popular_pages: int = Field(
        0,
        ge=0,
        le=5,
        description="popular 목록 페이지 수 (tmdb_id·query 없을 때)",
    )
    top_rated_pages: int = Field(
        0,
        ge=0,
        le=5,
        description="top_rated 목록 페이지 수 (tmdb_id·query 없을 때)",
    )


class KoficImportRequestSchema(BaseModel):
    target_date: str | None = Field(
        None,
        pattern=r"^\d{8}$",
        description="집계 기준일 YYYYMMDD (없으면 전일)",
    )
    week_gb: Literal["0", "1", "2"] = Field(
        "0",
        description="0=주간(전체) · 1=주중 · 2=주말",
    )
