"""TMDB credits(cast/crew) 백필 — mova actors/characters/movie_directors 채우기.

일회성 수동 실행 전용. seed_catalog_if_sparse/KOFIC 스케줄러와는 무관하며
부팅 흐름을 타지 않는다 — 반드시 명시적으로 실행해야 한다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_credits_cli.py
  (로컬 실행 시) python scripts/backfill_credits_cli.py
"""

from __future__ import annotations

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


async def _main() -> None:
    result = await backfill_credits()
    print(
        f"[backfill_credits] succeeded={result.succeeded} "
        f"failed={result.failed} skipped={result.skipped}"
    )
    if result.failed_slugs:
        print(f"[backfill_credits] failed_slugs={result.failed_slugs}")


if __name__ == "__main__":
    asyncio.run(_main())
