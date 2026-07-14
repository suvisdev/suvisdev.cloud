"""TMDB 인기/평점 순 영화를 모아 mova 스키마 기반 학습용 데이터셋(JSONL)을 생성한다.

용도: EXAONE RAG 코퍼스 / 파인튜닝 / few-shot 예시 데이터의 공통 원본.
출력: apps/mova/_docs/mova_movie_dataset.jsonl (한 줄당 영화 1편)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps"))

from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter, TmdbAdapterError  # noqa: E402
from mova.adapter.outbound.http.tmdb_mapper import tmdb_rating, tmdb_release_year  # noqa: E402

TARGET_COUNT = 300
PAGES_PER_ENDPOINT = 8  # popular/top_rated 각각 최대 20편 * 8페이지 = 160편 → dedup 후 300편 목표
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "apps", "mova", "_docs", "mova_movie_dataset.jsonl"
)


def _extract_cast(detail: dict, *, limit: int = 8) -> list[dict]:
    cast = (detail.get("credits") or {}).get("cast") or []
    result = []
    for member in cast[:limit]:
        name = str(member.get("name") or "").strip()
        character = str(member.get("character") or "").strip()
        if name:
            result.append({"actor_name": name, "character_name": character})
    return result


def _extract_genres(detail: dict) -> list[str]:
    return [str(g.get("name")).strip() for g in detail.get("genres") or [] if g.get("name")]


async def _collect_movie_ids(client: TmdbAdapter) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for endpoint in ("popular", "top_rated"):
        for page in range(1, PAGES_PER_ENDPOINT + 1):
            if endpoint == "popular":
                rows = await client.fetch_popular(page=page)
            else:
                rows = await client.fetch_top_rated(page=page)
            if not rows:
                break
            for row in rows:
                tmdb_id = row.get("id")
                if tmdb_id is not None and int(tmdb_id) not in seen:
                    seen.add(int(tmdb_id))
                    ids.append(int(tmdb_id))
            if len(ids) >= TARGET_COUNT:
                return ids[:TARGET_COUNT]
    return ids[:TARGET_COUNT]


async def main() -> None:
    api_key = os.getenv("TMDB_API_KEY", "")
    client = TmdbAdapter(api_key)

    movie_ids = await _collect_movie_ids(client)
    print(f"수집 대상 {len(movie_ids)}편")

    records = []
    for i, tmdb_id in enumerate(movie_ids, start=1):
        try:
            detail = await client.fetch_movie_detail(tmdb_id)
        except TmdbAdapterError as e:
            print(f"[{i}/{len(movie_ids)}] tmdb_id={tmdb_id} 실패: {e}")
            continue

        record = {
            "tmdb_id": tmdb_id,
            "slug": f"tmdb-{tmdb_id}",
            "title": str(detail.get("title") or "").strip(),
            "release_year": tmdb_release_year(str(detail.get("release_date") or "")),
            "rating": tmdb_rating(detail.get("vote_average")),
            "poster_url": client.poster_url(str(detail.get("poster_path") or "")),
            "genres": _extract_genres(detail),
            "overview": str(detail.get("overview") or "").strip(),
            "cast": _extract_cast(detail),
        }
        if record["title"] and record["overview"]:
            records.append(record)
        if i % 20 == 0:
            print(f"[{i}/{len(movie_ids)}] 진행 중...")
        await asyncio.sleep(0.05)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"완료: {len(records)}편 저장 → {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
