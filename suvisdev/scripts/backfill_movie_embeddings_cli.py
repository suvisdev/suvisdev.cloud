"""movies.embedding 백필 — title/genres/cast/synopsis로 Gemini 임베딩을 생성한다.

일회성 수동 실행 전용. `embedding IS NULL`인 영화 전부(TMDB·KOFIC 무관 — TMDB
재조회가 필요 없어 origin_country류와 달리 `slug LIKE 'tmdb-%'` 제한이 없다)가
대상. `GeminiEmbeddingAdapter`(ontology Hub 소속, mova는 Spoke→Hub 임포트라
`suvisdev/CLAUDE.md` O.4 기준 허용)를 그대로 재사용한다 — hub_knowledge와 같은
임베딩 백엔드/차원(768)을 쓰지만 **완전히 다른 컬럼(movies.embedding)**이라
hub_knowledge 재임베딩 이슈(PROGRESS.md 1순위, 프로덕션 데이터 삭제 보류 중)와
무관하다. 이 컬럼은 지금까지 한 번도 채워진 적이 없어(전량 NULL) 초기 백필일
뿐 재임베딩이 아니다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/backfill_movie_embeddings_cli.py
  (로컬 실행 시) python scripts/backfill_movie_embeddings_cli.py

  --limit N   앞 N편만 처리(시험 실행용, 예: --limit 5)
  --dry-run   임베딩 호출만 하고 DB write는 생략, 벡터 차원만 로그로 출력
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
logger = logging.getLogger("backfill_movie_embeddings")

_GEMINI_SLEEP_SECONDS = 0.5


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="앞 N편만 처리(기본값 없음 — 전량 실행)")
    parser.add_argument(
        "--dry-run", action="store_true", help="DB write 없이 임베딩 호출 결과만 로그로 출력"
    )
    return parser.parse_args(argv)


def _build_embedding_text(detail) -> str:
    """title/genres/cast(배우 5명)/synopsis — ingest_hub_knowledge.py의 텍스트 구성과 같은 결을 따른다."""
    lines = [detail.title]
    if detail.genres:
        lines.append(f"장르: {', '.join(detail.genres)}")
    cast_names = [a.name for a in detail.actors if a.role_type == "actor"][:5]
    if cast_names:
        lines.append(f"출연: {', '.join(cast_names)}")
    if detail.synopsis:
        lines.append(detail.synopsis)
    return "\n".join(lines)


async def _backfill_one(movies_repo, embedder, movie_id: int, slug: str, *, dry_run: bool) -> str:
    """영화 한 편 처리. 반환값: 'succeeded' | 'failed' | 'skipped'."""
    from ontology.app.ports.output.hub_rag_errors import HubRagError

    detail = await movies_repo.get_by_slug(slug)
    if detail is None:
        logger.warning("[backfill_movie_embeddings] 조회 실패, 스킵 | slug=%s", slug)
        return "skipped"

    text = _build_embedding_text(detail)
    try:
        vector = await embedder.embed(text)
    except HubRagError:
        logger.warning(
            "[backfill_movie_embeddings] 임베딩 호출 실패 | slug=%s", slug, exc_info=True
        )
        return "failed"

    if dry_run:
        print(f"[backfill_movie_embeddings] (dry-run) slug={slug} dim={len(vector)}")
    else:
        await movies_repo.update_embedding(movie_id, vector)
    return "succeeded"


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
    from ontology.adapter.outbound.llm.gemini_embedding_adapter import GeminiEmbeddingAdapter

    # get_keymaker()가 .env 로드의 부작용을 갖는다 — get_mova_session_factory()보다
    # 먼저 호출해야 MOVA_DATABASE_URL이 os.environ에 실린다(다른 backfill_*_cli.py와 동일 순서).
    get_keymaker()
    factory = get_mova_session_factory()
    embedder = GeminiEmbeddingAdapter()

    stats = {"succeeded": 0, "failed": 0, "skipped": 0}

    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        targets = await movies_repo.list_missing_embedding(limit=args.limit)
        print(f"[backfill_movie_embeddings] 대상 {len(targets)}편")

        for movie_id, slug in targets:
            outcome = await _backfill_one(movies_repo, embedder, movie_id, slug, dry_run=args.dry_run)
            stats[outcome] += 1
            await asyncio.sleep(_GEMINI_SLEEP_SECONDS)

    print(
        f"[backfill_movie_embeddings] 완료 succeeded={stats['succeeded']} "
        f"failed={stats['failed']} skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
