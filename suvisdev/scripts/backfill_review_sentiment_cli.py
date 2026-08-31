"""reviews.sentiment_label 백필 — body가 있는데 sentiment가 NULL인 리뷰를 순회한다.

GPU(CUDA)가 있는 로컬 머신에서만 실행한다. EXAONE-3.5-2.4B + Echo LoRA를
호출당 로드/해제하므로 건당 수십 초가 걸린다 — 대량 처리 시 --limit으로 끊어서
실행하는 것을 권장한다.

Usage (suvisdev 폴더에서):
  python scripts/backfill_review_sentiment_cli.py
  python scripts/backfill_review_sentiment_cli.py --limit 20
  python scripts/backfill_review_sentiment_cli.py --dry-run
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
logger = logging.getLogger("backfill_review_sentiment")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="앞 N건만 처리(기본값 없음 — 전량 실행)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="모델 호출 없이 대상 카운트만 로그로 출력"
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    import torch

    if not torch.cuda.is_available():
        print("[backfill_review_sentiment] CUDA GPU가 없습니다. 이 스크립트는 GPU 머신에서만 실행 가능합니다.")
        return

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from mova.app.use_cases.review_sentiment_backfill_interactor import (
        ReviewSentimentBackfillInteractor,
    )

    use_case = ReviewSentimentBackfillInteractor(
        session_factory=get_mova_session_factory(),
    )

    if args.dry_run:
        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        factory = use_case._session_factory  # noqa: SLF001 — CLI 전용 진입점
        async with factory() as session:
            targets = await ReviewsPgRepository(session=session).list_missing_sentiment(
                limit=args.limit
            )
        print(f"[backfill_review_sentiment] (dry-run) 대상 {len(targets)}건")
        return

    stats = await use_case.analyze_missing(limit=args.limit)
    print(
        f"[backfill_review_sentiment] 완료 succeeded={stats['succeeded']} "
        f"failed={stats['failed']} skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
