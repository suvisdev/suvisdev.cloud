"""TMDB 키워드 → 한국어 키워드 태그 백필 — mova tags(kind=mood) 채우기.

`/movie/{id}/keywords`의 영어 키워드를 `tmdb_keyword_map.TMDB_KEYWORD_TO_LABEL`
사전으로 한국어 라벨로 바꿔 tags에 넣는다. 사전에 없는 키워드는 버린다(채팅
태그 매칭이 한국어 ILIKE라 영어 태그는 검색에 안 걸림). 기존 태그와의 중복은
UNIQUE(movie_id, slug) ON CONFLICT DO NOTHING으로 건너뛴다.

일회성 수동 실행 전용(부팅 흐름 미포함). Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_tmdb_keyword_tags.py
  (로컬 실행 시) python scripts/backfill_tmdb_keyword_tags.py

  --limit N   앞 N편만 처리(시험 실행용, 예: --limit 5)
  --dry-run   TMDB fetch만 하고 DB write는 생략, 라벨만 로그 출력
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t%(message)s")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from core.matrix.grid_oracle_database_manager import get_mova_session_factory  # noqa: E402
from core.matrix.vauly_keymaker_secret_manager import keymaker  # noqa: E402
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter, TmdbAdapterError  # noqa: E402
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie  # noqa: E402
from mova.adapter.outbound.orm.studio_tags_orm import (  # noqa: E402
    TAG_KIND_MOOD,
    MovaTag,
    slugify_tag,
)
from mova.domain.value_objects.tmdb_keyword_map import TMDB_KEYWORD_TO_LABEL  # noqa: E402

_TMDB_SLUG_PREFIX = "tmdb-"

logger = logging.getLogger("backfill_keyword_tags")


def _parse_tmdb_id(slug: str) -> int | None:
    if not slug.startswith(_TMDB_SLUG_PREFIX):
        return None
    try:
        return int(slug[len(_TMDB_SLUG_PREFIX) :])
    except ValueError:
        return None


async def run(limit: int | None, dry_run: bool) -> None:
    factory = get_mova_session_factory()
    tmdb = TmdbAdapter(keymaker.tmdb_api_key)

    async with factory() as session:
        rows = await session.execute(select(MovaMovie.id, MovaMovie.slug).order_by(MovaMovie.id))
        movies = [(mid, slug) for mid, slug in rows if slug]
    if limit is not None:
        movies = movies[:limit]

    stats = {"movies": 0, "tagged_movies": 0, "inserted": 0, "skipped_slug": 0, "failed": 0}
    for movie_id, slug in movies:
        tmdb_id = _parse_tmdb_id(slug)
        if tmdb_id is None:
            stats["skipped_slug"] += 1
            continue
        stats["movies"] += 1
        try:
            keywords = await tmdb.fetch_movie_keywords(tmdb_id)
        except TmdbAdapterError as e:
            logger.warning("fetch 실패 movie_id=%s slug=%s — %s", movie_id, slug, e)
            stats["failed"] += 1
            continue

        labels = sorted({TMDB_KEYWORD_TO_LABEL[k] for k in keywords if k in TMDB_KEYWORD_TO_LABEL})
        if not labels:
            continue
        if dry_run:
            logger.info("[dry-run] movie_id=%s slug=%s labels=%s", movie_id, slug, labels)
            stats["tagged_movies"] += 1
            continue

        async with factory() as session:
            result = await session.execute(
                pg_insert(MovaTag)
                .values(
                    [
                        {
                            "movie_id": movie_id,
                            "tag_kind": TAG_KIND_MOOD,
                            "slug": slugify_tag(label),
                            "label": label,
                            "description": "",
                        }
                        for label in labels
                    ]
                )
                .on_conflict_do_nothing(index_elements=["movie_id", "slug"])
                .returning(MovaTag.id)
            )
            await session.commit()
        # ON CONFLICT 벌크 insert는 rowcount가 -1로 나올 수 있어 RETURNING으로 센다.
        inserted = len(result.fetchall())
        stats["tagged_movies"] += 1
        stats["inserted"] += inserted
        if inserted:
            logger.info("movie_id=%s +%d태그 %s", movie_id, inserted, labels)

    logger.info(
        "완료 — 대상 %d편(태그 생성 %d편, 신규 태그 %d개, slug 스킵 %d, 실패 %d)",
        stats["movies"],
        stats["tagged_movies"],
        stats["inserted"],
        stats["skipped_slug"],
        stats["failed"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="앞 N편만 처리(시험 실행용)")
    parser.add_argument("--dry-run", action="store_true", help="DB write 없이 라벨만 로그 출력")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.dry_run))


if __name__ == "__main__":
    main()
