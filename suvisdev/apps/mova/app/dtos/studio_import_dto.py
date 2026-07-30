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
    release_year: int
    rating: float
    poster_url: str
    genres: list[str]
    # movies 테이블에는 저장하지 않고 Hub(ontology) RAG 색인용으로만 쓴다 (hub_rag.ingest_movie).
    overview: str = ""
    cast: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TmdbCastMemberDto:
    """TMDB credits.cast[] 한 명 — actors/characters 백필용(map_cast_names의 이름만 추출과 다름)."""

    tmdb_person_id: int
    name: str
    character: str
    order: int
    profile_photo_url: str = ""


@dataclass(frozen=True)
class TmdbDirectorDto:
    """TMDB credits.crew[] 중 job == 'Director'인 인물."""

    tmdb_person_id: int
    name: str
    profile_photo_url: str = ""


@dataclass(frozen=True)
class TmdbCreditsDto:
    """TMDB 영화 상세(append_to_response=credits) 한 편 분량의 cast/crew."""

    cast: list[TmdbCastMemberDto] = field(default_factory=list)
    directors: list[TmdbDirectorDto] = field(default_factory=list)


@dataclass(frozen=True)
class MovieUpsertCommand:
    slug: str
    title: str
    release_year: int
    rating: float
    poster_url: str
    genres: list[str]
    age_rating: str | None = None
    platforms: list[dict[str, str | None]] = field(default_factory=list)


@dataclass(frozen=True)
class TmdbImportCommand:
    """수동 TMDB 수입 — tmdb_id · query · popular_pages · top_rated_pages 중 하나만 사용."""

    tmdb_id: int | None = None
    query: str | None = None
    popular_pages: int = 0
    top_rated_pages: int = 0


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


@dataclass(frozen=True)
class CreditsBackfillResultDto:
    """TMDB credits 백필 1회 실행 결과. _ingest_to_hub와 달리 실패를 조용히 삼키지 않고 집계한다."""

    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    failed_slugs: list[str] = field(default_factory=list)
