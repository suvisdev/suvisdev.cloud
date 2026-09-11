"""movies.original_language 백필 — TMDB `original_language` 재조회로 채운다.

일회성 수동 실행 전용. `original_language IS NULL`인 TMDB 원산 영화(`slug`
`tmdb-*`)만 대상 — KOFIC 영화는 TMDB id가 없어 이 스크립트로 채울 수 없다
(전부 한국 박스오피스 데이터라 언어 필터의 관심 대상도 아님). 이미 값이
채워진 로우는 `list_missing_original_language()` 쿼리 자체가 제외하므로
재실행해도 idempotent하다.

Usage (suvisdev 폴더에서):
  kubectl -n suvisdev exec deploy/backend -- python scripts/backfill_original_language_cli.py
  (로컬 실행 시) python scripts/backfill_original_language_cli.py

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
logger = logging.getLogger("backfill_original_language")

_TMDB_SLEEP_SECONDS = 0.25


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="앞 N편만 처리(기본값 없음 — 전량 실행)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="DB write 없이 TMDB fetch 결과만 로그로 출력"
    )
    return parser.parse_args(argv)


async def _backfill_one(movies_repo, catalog, movie_id: int, slug: str, *, dry_run: bool) -> str:
    """영화 한 편 처리. 반환값: 'succeeded' | 'failed' | 'skipped'."""
    from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapterError

    tmdb_id_raw = slug.removeprefix("tmdb-")
    if not tmdb_id_raw.isdigit():
        logger.warning("[backfill_original_language] tmdb slug 아님, 스킵 | slug=%s", slug)
        return "skipped"

    try:
        snap = await catalog.fetch_by_id(int(tmdb_id_raw))
    except (TmdbAdapterError, ValueError):
        logger.warning(
            "[backfill_original_language] TMDB fetch 실패 | slug=%s", slug, exc_info=True
        )
        return "failed"

    if not snap.original_language:
        return "skipped"

    if dry_run:
        print(
            f"[backfill_original_language] (dry-run) slug={slug} "
            f"original_language={snap.original_language!r}"
        )
    else:
        await movies_repo.update_original_language(movie_id, snap.original_language)
    return "succeeded"


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository

    keymaker = get_keymaker()
    factory = get_mova_session_factory()
    catalog = TmdbCatalogAdapter(keymaker.tmdb_api_key)

    stats = {"succeeded": 0, "failed": 0, "skipped": 0}

    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        targets = await movies_repo.list_missing_original_language(limit=args.limit)
        print(f"[backfill_original_language] 대상 {len(targets)}편")

        for movie_id, slug in targets:
            outcome = await _backfill_one(
                movies_repo, catalog, movie_id, slug, dry_run=args.dry_run
            )
            stats[outcome] += 1
            await asyncio.sleep(_TMDB_SLEEP_SECONDS)

    print(
        f"[backfill_original_language] 완료 succeeded={stats['succeeded']} "
        f"failed={stats['failed']} skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
