from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StudioImportQuery:
    id: int
    name: str


@dataclass(frozen=True)
class StudioImportResponse:
    id: int
    name: str


@dataclass(frozen=True)
class TmdbMovieSnapshotDto:
    """TMDB API 한 편 분량 — DB upsert 전 정규화."""

    tmdb_id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    genres: list[str]


@dataclass(frozen=True)
class MovieUpsertCommand:
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    genres: list[str]
    age_rating: str | None = None
    platforms: list[dict[str, str | None]] = field(default_factory=list)


@dataclass(frozen=True)
class TmdbImportCommand:
    """수동 TMDB 수입 — tmdb_id · query · popular_pages 중 하나만 사용."""

    tmdb_id: int | None = None
    query: str | None = None
    popular_pages: int = 0


@dataclass(frozen=True)
class MovieImportResultDto:
    imported: int
    movie_ids: list[int] = field(default_factory=list)
    rankings_updated: bool = False
    message: str = ""

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_import_schema import MovieImportResultSchema

        return MovieImportResultSchema(
            imported=self.imported,
            movie_ids=self.movie_ids,
            rankings_updated=self.rankings_updated,
            message=self.message,
        )
