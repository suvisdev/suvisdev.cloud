"""뮤지컬 장르 태그 백필 — TMDB 키워드 기반.

TMDB 표준 장르에는 "뮤지컬"이 없어 레미제라블·라라랜드 같은 뮤지컬 영화가
드라마·로맨스 등으로만 들어온다. TMDB 키워드(musical 4344, broadway musical
165241, musical theater 220201)로 뮤지컬 영화를 discover 조회한 뒤, 카탈로그와
제목(정규화)+연도(±1)로 매칭해 tags에 '뮤지컬' genre 태그를 추가한다.

movies에 tmdb_id 컬럼이 없어 제목·연도 매칭을 쓴다. 이미 태그가 있으면 skip
하므로 재실행해도 안전하다(멱등).

Usage (backend 컨테이너 안):
  docker exec suvisdevcloud-backend-1 python scripts/tag_musical_genre.py --dry-run
  docker exec suvisdevcloud-backend-1 python scripts/tag_musical_genre.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t%(message)s")
logger = logging.getLogger(__name__)

_MUSICAL_KEYWORD_IDS = "4344|165241|220201"
_MIN_VOTE_COUNT = 100
_LABEL = "뮤지컬"


def _norm_title(title: str) -> str:
    return re.sub(r"[\s:·\-!?,.]", "", title).lower()


async def _run(dry_run: bool) -> None:
    from sqlalchemy import select

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter
    from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
    from mova.adapter.outbound.orm.studio_tags_orm import (
        TAG_KIND_GENRE,
        MovaTag,
        slugify_tag,
    )

    tmdb = TmdbAdapter(get_keymaker().tmdb_api_key)

    # 1) TMDB 뮤지컬 키워드 영화 전 페이지 수집 → {정규화 제목: [연도]}
    tmdb_musicals: dict[str, list[int]] = {}
    page = 1
    while True:
        rows = await tmdb.fetch_discover(
            page=page,
            with_keywords=_MUSICAL_KEYWORD_IDS,
            vote_count_gte=_MIN_VOTE_COUNT,
        )
        if not rows:
            break
        for m in rows:
            year = int((m.get("release_date") or "0")[:4] or 0)
            tmdb_musicals.setdefault(_norm_title(m.get("title") or ""), []).append(year)
        page += 1
        await asyncio.sleep(0.25)
    logger.info("[tag_musical] TMDB 뮤지컬 후보 %d편(%d페이지)", len(tmdb_musicals), page - 1)

    # 2) 카탈로그 매칭 + 태그 추가
    factory = get_mova_session_factory()
    added = matched = 0
    async with factory() as session:
        movies = (await session.execute(select(MovaMovie))).scalars().all()
        for movie in movies:
            years = tmdb_musicals.get(_norm_title(movie.title))
            if not years or not any(abs((movie.release_year or 0) - y) <= 1 for y in years):
                continue
            matched += 1
            slug = slugify_tag(_LABEL)
            exists = await session.execute(
                select(MovaTag.id).where(
                    MovaTag.movie_id == movie.id,
                    MovaTag.slug == slug,
                )
            )
            if exists.first():
                continue
            logger.info("[tag_musical] + %s (%s, id=%d)", movie.title, movie.release_year, movie.id)
            if dry_run:
                added += 1
                continue
            session.add(
                MovaTag(
                    movie_id=movie.id,
                    tag_kind=TAG_KIND_GENRE,
                    slug=slug,
                    label=_LABEL,
                )
            )
            added += 1
        if not dry_run:
            await session.commit()
    print(f"DONE — 매칭 {matched} / 태그 추가 {added}{' (dry-run)' if dry_run else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="태그를 실제로 넣지 않고 대상만 출력"
    )
    args = parser.parse_args()
    asyncio.run(_run(args.dry_run))
