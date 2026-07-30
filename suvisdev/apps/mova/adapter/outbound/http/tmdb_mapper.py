"""TMDB JSON → Mova import DTO 매핑."""

from __future__ import annotations

from mova.adapter.outbound.http.tmdb_adapter import build_image_url
from mova.app.dtos.studio_import_dto import (
    TmdbCastMemberDto,
    TmdbCreditsDto,
    TmdbDirectorDto,
    TmdbMovieSnapshotDto,
)


def tmdb_slug(tmdb_id: int) -> str:
    return f"tmdb-{int(tmdb_id)}"


def tmdb_rating(vote_average: object) -> float:
    try:
        value = float(vote_average)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return round(min(5.0, value / 2.0), 1)


def tmdb_release_year(release_date: str | None) -> int:
    if not release_date or len(release_date) < 4:
        return 0
    try:
        return int(release_date[:4])
    except ValueError:
        return 0


def map_genre_ids(genre_ids: list[object], genre_map: dict[int, str]) -> list[str]:
    names: list[str] = []
    for raw in genre_ids:
        try:
            gid = int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        name = genre_map.get(gid)
        if name and name not in names:
            names.append(name)
    return names


def map_genre_objects(genres: list[object]) -> list[str]:
    names: list[str] = []
    for item in genres:
        if isinstance(item, dict):
            label = str(item.get("name") or "").strip()
            if label and label not in names:
                names.append(label)
    return names


def map_cast_names(credits: object, *, limit: int = 5) -> list[str]:
    """TMDB append_to_response=credits의 cast 상위 N명 이름만 추출. RAG 색인용."""
    if not isinstance(credits, dict):
        return []
    names: list[str] = []
    for member in credits.get("cast") or []:
        if isinstance(member, dict):
            name = str(member.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
        if len(names) >= limit:
            break
    return names


def map_credits(credits: object, *, cast_limit: int = 10) -> TmdbCreditsDto:
    """TMDB append_to_response=credits 전체를 actors/characters 백필용으로 매핑.

    map_cast_names()(hub_rag 텍스트 색인용, 이름만 상위 5명)와는 별개 — 이쪽은
    person id/character/order/crew까지 보존한다.
    """
    if not isinstance(credits, dict):
        return TmdbCreditsDto()

    cast: list[TmdbCastMemberDto] = []
    seen_person_ids: set[int] = set()
    for member in credits.get("cast") or []:
        if not isinstance(member, dict):
            continue
        person_id = member.get("id")
        name = str(member.get("name") or "").strip()
        if person_id is None or not name:
            continue
        try:
            pid = int(person_id)
        except (TypeError, ValueError):
            continue
        if pid in seen_person_ids:
            continue
        seen_person_ids.add(pid)
        cast.append(
            TmdbCastMemberDto(
                tmdb_person_id=pid,
                name=name,
                character=str(member.get("character") or "").strip(),
                order=int(member.get("order") or 0),
                profile_photo_url=build_image_url(member.get("profile_path")),
            )
        )
        if len(cast) >= cast_limit:
            break

    directors: list[TmdbDirectorDto] = []
    seen_director_ids: set[int] = set()
    for member in credits.get("crew") or []:
        if not isinstance(member, dict) or member.get("job") != "Director":
            continue
        person_id = member.get("id")
        name = str(member.get("name") or "").strip()
        if person_id is None or not name:
            continue
        try:
            pid = int(person_id)
        except (TypeError, ValueError):
            continue
        if pid in seen_director_ids:
            continue
        seen_director_ids.add(pid)
        directors.append(
            TmdbDirectorDto(
                tmdb_person_id=pid,
                name=name,
                profile_photo_url=build_image_url(member.get("profile_path")),
            )
        )

    return TmdbCreditsDto(cast=cast, directors=directors)


def map_tmdb_row(
    row: dict,
    *,
    genre_map: dict[int, str],
    poster_url: str,
) -> TmdbMovieSnapshotDto | None:
    tmdb_id = row.get("id")
    title = str(row.get("title") or row.get("name") or "").strip()
    if tmdb_id is None or not title:
        return None
    genre_ids = list(row.get("genre_ids") or [])
    genres = map_genre_ids(genre_ids, genre_map)
    if not genres and row.get("genres"):
        genres = map_genre_objects(list(row.get("genres") or []))
    return TmdbMovieSnapshotDto(
        tmdb_id=int(tmdb_id),
        slug=tmdb_slug(int(tmdb_id)),
        title=title,
        release_year=tmdb_release_year(str(row.get("release_date") or "")),
        rating=tmdb_rating(row.get("vote_average")),
        poster_url=poster_url,
        genres=genres,
        overview=str(row.get("overview") or "").strip(),
        cast=map_cast_names(row.get("credits")),
    )
