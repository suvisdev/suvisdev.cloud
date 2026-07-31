"""TMDB credits(cast/crew) 백필 — mova actors/characters/movie_directors 채우기.

일회성 수동 실행 전용. seed_catalog_if_sparse/KOFIC 스케줄러와는 무관하며
부팅 흐름을 타지 않는다 — 반드시 명시적으로 실행해야 한다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_credits_cli.py
  (로컬 실행 시) python scripts/backfill_credits_cli.py

  --limit N   앞 N편만 처리(시험 실행용, 예: --limit 3)
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

from mova.dependencies.credits_backfill_provider import backfill_credits  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="앞 N편만 처리(기본값 없음 — 전량 실행)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB write 없이 TMDB fetch 결과만 로그로 출력",
    )
    return parser.parse_args(argv)


async def _main(args: argparse.Namespace) -> None:
    if args.dry_run:
        print("[backfill_credits] dry-run 모드 — DB write 없음")
    if args.limit is not None:
        print(f"[backfill_credits] limit={args.limit}편만 처리")

    result = await backfill_credits(limit=args.limit, dry_run=args.dry_run)
    print(
        f"[backfill_credits] succeeded={result.succeeded} "
        f"failed={result.failed} skipped={result.skipped}"
    )
    if result.failed_slugs:
        print(f"[backfill_credits] failed_slugs={result.failed_slugs}")


if __name__ == "__main__":
    asyncio.run(_main(_parse_args()))
