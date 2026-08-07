"""movies.origin_country 백필 — TMDB `origin_country` 재조회로 채운다.

일회성 수동 실행 전용. `origin_country IS NULL`인 TMDB 원산 영화(`slug`
`tmdb-*`)만 대상 — KOFIC 영화는 TMDB id가 없어 이 스크립트로 채울 수 없다
(전부 한국 영화라 국가 필터로 걸러낼 이유도 없음). 이미 값이 채워진 로우는
`list_missing_origin_country()` 쿼리 자체가 제외하므로 재실행해도 idempotent하다.

**TMDB가 빈 배열을 준 경우에도 `[]`를 기록한다** — NULL로 남기면 "아직 백필
안 됨"과 구분이 안 돼 매 실행마다 같은 영화를 다시 조회하게 된다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_origin_country_cli.py
  (로컬 실행 시) python scripts/backfill_origin_country_cli.py

  --limit N   앞 N편만 처리(시험 실행용, 예: --limit 5)
  --dry-run   TMDB fetch만 하고 DB write는 생략, 무엇이 들어갈지 로그만 출력
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
logger = logging.getLogger("backfill_origin_country")

_TMDB_SLEEP_SECONDS = 0.25


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="앞 N편만 처리(기본값 없음 — 전량 실행)")
    parser.add_argument(
        "--dry-run", action="store_true", help="DB write 없이 TMDB fetch 결과만 로그로 출력"
    )
    return parser.parse_args(argv)


async def _backfill_one(movies_repo, catalog, movie_id: int, slug: str, *, dry_run: bool) -> str:
    """영화 한 편 처리. 반환값: 'succeeded' | 'failed' | 'skipped' | 'empty'.

    'empty'는 TMDB에 국가 정보가 없는 정상 케이스 — 그래도 `[]`를 기록해
    다음 실행에서 다시 조회하지 않게 한다('skipped'는 write 자체를 안 한 것).
    """
    from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapterError

    tmdb_id_raw = slug.removeprefix("tmdb-")
    if not tmdb_id_raw.isdigit():
        logger.warning("[backfill_origin_country] tmdb slug 아님, 스킵 | slug=%s", slug)
        return "skipped"

    try:
        snap = await catalog.fetch_by_id(int(tmdb_id_raw))
    except (TmdbAdapterError, ValueError):
        logger.warning("[backfill_origin_country] TMDB fetch 실패 | slug=%s", slug, exc_info=True)
        return "failed"

    if dry_run:
        print(
            f"[backfill_origin_country] (dry-run) slug={slug} "
            f"origin_country={snap.origin_country!r}"
        )
    else:
        await movies_repo.update_origin_country(movie_id, snap.origin_country)
    return "succeeded" if snap.origin_country else "empty"


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository

    keymaker = get_keymaker()
    factory = get_mova_session_factory()
    catalog = TmdbCatalogAdapter(keymaker.tmdb_api_key)

    stats = {"succeeded": 0, "failed": 0, "skipped": 0, "empty": 0}

    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        targets = await movies_repo.list_missing_origin_country(limit=args.limit)
        print(f"[backfill_origin_country] 대상 {len(targets)}편")

        for movie_id, slug in targets:
            outcome = await _backfill_one(movies_repo, catalog, movie_id, slug, dry_run=args.dry_run)
            stats[outcome] += 1
            await asyncio.sleep(_TMDB_SLEEP_SECONDS)

    print(
        f"[backfill_origin_country] 완료 succeeded={stats['succeeded']} "
        f"empty={stats['empty']} failed={stats['failed']} skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
