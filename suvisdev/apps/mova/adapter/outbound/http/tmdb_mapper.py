"""TMDB JSON → Mova import DTO 매핑."""

from __future__ import annotations

from typing import Any

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


def map_genre_ids(genre_ids: list[Any], genre_map: dict[int, str]) -> list[str]:
    names: list[str] = []
    for raw in genre_ids:
        try:
            gid = int(raw)
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
    row: dict[str, Any],
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
        original_language=str(row.get("original_language") or "").strip().lower(),
        origin_country=[
            str(c).strip().upper() for c in (row.get("origin_country") or []) if str(c).strip()
        ],
        age_rating=map_kr_certification(row.get("release_dates")),
        platforms=map_kr_watch_providers(row.get("watch/providers")),
        trailer_key=map_youtube_trailer(row.get("videos")),
    )


# TMDB KR release_dates.certification 실측값(2026-08-09, 인터스텔라/조커/겨울왕국2
# 등 표본 확인) — "전체"/"12세"/"15세"/"청불" 4단계는 studio_movies_router.py의
# age_rating 필터 설명과 맞춘 것. 매핑 밖 값(빈 문자열 등)은 None으로 둔다.
_KR_CERTIFICATION_MAP = {
    "ALL": "전체",
    "12": "12세",
    "15": "15세",
    "18": "청불",
    "19": "청불",
}


def map_kr_certification(release_dates: dict[str, Any] | None) -> str | None:
    """TMDB `release_dates`(append_to_response) → KR 등급. KR 자체가 없거나
    certification이 매핑 밖이면 None(억지로 추측하지 않음)."""
    if not release_dates:
        return None
    for entry in release_dates.get("results") or []:
        if entry.get("iso_3166_1") != "KR":
            continue
        for rd in entry.get("release_dates") or []:
            cert = str(rd.get("certification") or "").strip().upper()
            if cert in _KR_CERTIFICATION_MAP:
                return _KR_CERTIFICATION_MAP[cert]
        return None
    return None


def _normalize_provider_key(name: str) -> str:
    """ "Disney Plus" → "disneyplus" — studio_movies_router.py의 platform 필터가
    쓰는 소문자·공백 없는 provider 키와 맞춘다."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def map_kr_watch_providers(watch_providers: dict[str, Any] | None) -> list[dict[str, str | None]]:
    """TMDB `watch/providers`(append_to_response) → PlatformDto 호환 dict 리스트.

    TMDB는 provider별 개별 딥링크를 주지 않는다 — 국가 단위 링크(JustWatch 경유)
    하나뿐이라 모든 provider가 같은 url을 공유한다. flatrate(구독)·rent·buy 순으로
    훑어 같은 provider가 여러 유형에 걸치면 먼저 나온 유형만 남긴다.
    """
    if not watch_providers:
        return []
    kr = (watch_providers.get("results") or {}).get("KR")
    if not kr:
        return []
    link = kr.get("link")
    seen: set[str] = set()
    platforms: list[dict[str, str | None]] = []
    for kind in ("flatrate", "rent", "buy"):
        for p in kr.get(kind) or []:
            name = str(p.get("provider_name") or "").strip()
            if not name:
                continue
            key = _normalize_provider_key(name)
            if key in seen:
                continue
            seen.add(key)
            platforms.append({"provider": key, "url": link, "type": kind})
    return platforms


def map_youtube_trailer(videos: dict[str, Any] | None) -> str | None:
    """TMDB `videos`(append_to_response, `include_video_language=ko,en,null`로
    요청해 한국어 트레일러가 없어도 폴백이 있게 함) → YouTube video key 하나.

    site=YouTube만 대상(Vimeo 등은 프론트 임베드 방식이 달라 지금은 스코프 밖).
    type=Trailer·official·ko 순으로 우선순위를 매겨 가장 적합한 한 편만 고른다.
    """
    if not videos:
        return None
    results = [
        v for v in (videos.get("results") or []) if v.get("site") == "YouTube" and v.get("key")
    ]
    if not results:
        return None

    def _rank(v: dict[str, Any]) -> tuple[int, int, int]:
        return (
            0 if v.get("type") == "Trailer" else 1,
            0 if v.get("official") else 1,
            0 if v.get("iso_639_1") == "ko" else 1,
        )

    results.sort(key=_rank)
    return str(results[0]["key"])
