"""TMDB JSON → Mova import DTO 매핑."""

from __future__ import annotations

from mova.app.dtos.studio_import_dto import TmdbMovieSnapshotDto


def tmdb_slug(tmdb_id: int) -> str:
    return f"tmdb-{int(tmdb_id)}"


def tmdb_rating(vote_average: object) -> float:
    try:
        value = float(vote_average)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return round(min(5.0, value / 2.0), 1)


def tmdb_release_year(release_date: str | None) -> str:
    if not release_date or len(release_date) < 4:
        return ""
    return release_date[:4]


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
    )
