"""reviews.embedding 백필 — body가 있는데 embedding이 NULL인 리뷰를 순회한다.

BackgroundTasks가 정상적으로 돌면 신규/수정 리뷰는 저장 직후 임베딩까지
채워진다. 이 스크립트는 그 경로가 실패했거나 서버 재기동으로 유실된 리뷰를
잡는 **크론 안전망**이다. `embedding IS NULL AND body IS NOT NULL`만
대상이라 idempotent.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_review_embeddings_cli.py
  (로컬 실행 시) python scripts/backfill_review_embeddings_cli.py

  --limit N   앞 N건만 처리(시험 실행용)
  --dry-run   임베딩 호출 없이 대상 카운트만 출력

로그 인프라: `_docs/SCRIPTS_EXECUTION_GUIDE.md` — `>> ~/*.log 2>&1` 필수.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t%(message)s")
logger = logging.getLogger("backfill_review_embeddings")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="앞 N건만 처리(기본값 없음 — 전량 실행)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="임베딩 호출 없이 대상 카운트만 로그로 출력"
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker

    get_keymaker()

    from mova.app.use_cases.review_embedding_backfill_interactor import (
        ReviewEmbeddingBackfillInteractor,
    )
    from ontology.adapter.outbound.llm.gemini_embedding_adapter import GeminiEmbeddingAdapter

    backfill_key = os.getenv("GEMINI_BACKFILL_API_KEY", "").strip()
    backfill_client = None
    if backfill_key:
        from google import genai

        backfill_client = genai.Client(api_key=backfill_key)

    embedder = (
        GeminiEmbeddingAdapter(client=backfill_client)
        if backfill_client
        else GeminiEmbeddingAdapter()
    )
    use_case = ReviewEmbeddingBackfillInteractor(
        session_factory=get_mova_session_factory(),
        embedder=embedder,
    )

    if args.dry_run:
        from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository

        factory = use_case._session_factory  # noqa: SLF001 — CLI 전용 진입점
        async with factory() as session:
            targets = await ReviewsPgRepository(session=session).list_missing_embedding(
                limit=args.limit
            )
        print(f"[backfill_review_embeddings] (dry-run) 대상 {len(targets)}건")
        return

    stats = await use_case.embed_missing(limit=args.limit)
    print(
        f"[backfill_review_embeddings] 완료 succeeded={stats['succeeded']} "
        f"failed={stats['failed']} skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
