"""TMDB vote_count 백필 — movies.vote_count 채우기 (rating 노이즈 완화 시그널).

vote_count=0(미수집)인 tmdb- slug 영화를 순회하며 TMDB 기본 상세에서
vote_count를 가져와 저장한다. 멱등 — 재실행 시 이미 채워진 영화는 스킵.

일회성 수동 실행 전용(부팅 흐름 미포함). Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_vote_counts.py
  (로컬 실행 시) python scripts/backfill_vote_counts.py

  --limit N   앞 N편만 처리(시험 실행용)
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

from sqlalchemy import select, update  # noqa: E402

from core.matrix.grid_oracle_database_manager import get_mova_session_factory  # noqa: E402
from core.matrix.vauly_keymaker_secret_manager import keymaker  # noqa: E402
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter, TmdbAdapterError  # noqa: E402
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie  # noqa: E402

_TMDB_SLUG_PREFIX = "tmdb-"

logger = logging.getLogger("backfill_vote_counts")


async def run(limit: int | None) -> None:
    factory = get_mova_session_factory()
    tmdb = TmdbAdapter(keymaker.tmdb_api_key)

    async with factory() as session:
        rows = await session.execute(
            select(MovaMovie.id, MovaMovie.slug)
            .where(MovaMovie.vote_count == 0, MovaMovie.slug.like(f"{_TMDB_SLUG_PREFIX}%"))
            .order_by(MovaMovie.id)
        )
        movies = list(rows)
    if limit is not None:
        movies = movies[:limit]

    stats = {"updated": 0, "zero": 0, "failed": 0}
    for movie_id, slug in movies:
        try:
            tmdb_id = int(slug[len(_TMDB_SLUG_PREFIX) :])
        except ValueError:
            continue
        try:
            votes = await tmdb.fetch_movie_vote_count(tmdb_id)
        except TmdbAdapterError as e:
            logger.warning("fetch 실패 movie_id=%s slug=%s — %s", movie_id, slug, e)
            stats["failed"] += 1
            continue
        if votes <= 0:
            stats["zero"] += 1
            continue
        async with factory() as session:
            await session.execute(
                update(MovaMovie).where(MovaMovie.id == movie_id).values(vote_count=votes)
            )
            await session.commit()
        stats["updated"] += 1
        if stats["updated"] % 200 == 0:
            logger.info("진행 %d편 갱신", stats["updated"])

    logger.info(
        "완료 — 대상 %d편(갱신 %d, 투표0 %d, 실패 %d)",
        len(movies),
        stats["updated"],
        stats["zero"],
        stats["failed"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="앞 N편만 처리(시험 실행용)")
    args = parser.parse_args()
    asyncio.run(run(args.limit))


if __name__ == "__main__":
    main()
