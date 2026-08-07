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
    # Hub(ontology) RAG 색인(hub_rag.ingest_movie)과 movies.synopsis 양쪽에 쓰인다.
    overview: str = ""
    cast: list[str] = field(default_factory=list)
    original_language: str = ""


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
    synopsis: str | None = None
    original_language: str | None = None


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
class BackfillOneResultDto:
    """`_backfill_one()` 한 편 처리 결과 — cast/director 개별 실패 건수.

    2026-08-05: character_name VARCHAR(50) 초과 등 캐스트 1명의 실패가
    나머지 전원 + directors를 통째로 스킵시키던 문제 수정 이후, 그 통짜
    실패 대신 몇 명이 개별적으로 스킵됐는지를 이 dto로 노출한다.
    """

    skipped_cast: int = 0
    skipped_directors: int = 0


@dataclass(frozen=True)
class CreditsBackfillResultDto:
    """TMDB credits 백필 1회 실행 결과. _ingest_to_hub와 달리 실패를 조용히 삼키지 않고 집계한다."""

    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    skipped_cast: int = 0
    skipped_directors: int = 0
    failed_slugs: list[str] = field(default_factory=list)
