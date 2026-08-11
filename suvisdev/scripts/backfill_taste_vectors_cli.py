"""유저 취향 벡터 재계산 백필 — embedding+rating이 있는 리뷰를 가진 유저 전원.

BackgroundTasks가 정상적으로 돌면 리뷰 저장 직후 작성자 취향 벡터가 바로
갱신된다. 이 스크립트는 그 경로가 실패했거나 서버 재기동으로 유실된 유저를
잡는 **크론 안전망**이다. `recompute_for_user`가 idempotent해서(같은 유저를
다시 돌려도 같은 가중 평균이 나옴) 전량 재실행해도 안전하다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_taste_vectors_cli.py
  (로컬 실행 시) python scripts/backfill_taste_vectors_cli.py

  --limit N   앞 N명만 처리(시험 실행용)
  --dry-run   재계산 없이 대상 유저 수만 출력

로그 인프라: `_docs/SCRIPTS_EXECUTION_GUIDE.md` — `>> ~/*.log 2>&1` 필수.
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
logger = logging.getLogger("backfill_taste_vectors")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="앞 N명만 처리(기본값 없음 — 전량 실행)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="재계산 없이 대상 유저 수만 로그로 출력"
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    from mova.dependencies.platform_user_taste_vector_provider import (
        get_user_taste_vector_recompute_use_case,
    )

    use_case = get_user_taste_vector_recompute_use_case()

    if args.dry_run:
        # dry-run은 카운트만 — 재계산 자체를 돌리지 않는다.
        from mova.adapter.outbound.pg.platform_user_taste_vectors_pg_repository import (
            UserTasteVectorsPgRepository,
        )

        factory = use_case._session_factory  # noqa: SLF001 — CLI 전용 진입점
        async with factory() as session:
            repo = UserTasteVectorsPgRepository(session=session)
            user_ids = await repo.list_user_ids_with_rated_reviews(limit=args.limit)
        print(f"[backfill_taste_vectors] (dry-run) 대상 {len(user_ids)}명")
        return

    stats = await use_case.recompute_missing(limit=args.limit)
    print(f"[backfill_taste_vectors] 완료 updated={stats['updated']} cleared={stats['cleared']}")


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
