"""영화-컬렉션 배정/해제 CLI — 관리자 큐레이션 도구.

`scripts/seed_collections.sql`의 raw UPDATE를 대체하는 정식 경로.
Repository 직접 호출(SSH 전제, 배포 자동화가 아니라 사람이 돌리는
큐레이션 작업)이라 인증 가드는 걸지 않는다. API 엔드포인트는 별도로
`require_admin` 가드가 걸린 `PATCH/DELETE /mova/collections/{slug}/movies`
가 담당한다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/assign_collection_cli.py \
    --slug nolan-world --movie-ids 99,106,85 [--dry-run]
  docker compose exec backend python scripts/assign_collection_cli.py \
    --slug nolan-world --movie-ids 99,106,85 --unassign [--dry-run]

옵션:
  --slug <collection_slug>   대상 컬렉션 slug (필수)
  --movie-ids 1,2,3          쉼표 구분 movie.id 목록 (필수)
  --unassign                 배정 대신 해제(collection_id → NULL)
  --dry-run                  변경 예정 개수만 출력 (실제 UPDATE 없음)

시맨틱:
- 배정: movies.collection_id one-to-many라 다른 컬렉션에 이미 속한
  영화는 이 컬렉션으로 이동(덮어쓰기). moved_from_other_collection에
  카운트를 반환.
- 해제: 이 컬렉션에 속하지 않은 movie_id는 조용히 무시(idempotent),
  skipped_ids에 담아 반환.
- 부분 성공: DB에 없는 movie_id는 404 대신 skipped_ids로 반환.

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
logger = logging.getLogger("assign_collection")


def _parse_movie_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            ids.append(int(token))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"movie-ids에 정수가 아닌 값: {token!r}"
            ) from exc
    if not ids:
        raise argparse.ArgumentTypeError("movie-ids가 비어 있음")
    return ids


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", type=str, required=True, help="대상 컬렉션 slug")
    parser.add_argument(
        "--movie-ids",
        type=_parse_movie_ids,
        required=True,
        help="쉼표 구분 movie.id 목록 (예: 99,106,85)",
    )
    parser.add_argument(
        "--unassign",
        action="store_true",
        help="배정 대신 해제(collection_id → NULL)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="변경 예정 개수만 출력 — 실제 UPDATE 없음",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.pg.market_collections_pg_repository import (
        CollectionsPgRepository,
    )

    # get_keymaker()가 .env 로드 부작용 — session factory보다 먼저.
    get_keymaker()
    factory = get_mova_session_factory()

    async with factory() as session:
        repo = CollectionsPgRepository(session=session)

        if args.dry_run:
            entity = await repo._get_entity_by_slug(args.slug)  # noqa: SLF001 — CLI 전용 진입점
            if entity is None:
                print(f"[assign_collection] (dry-run) 컬렉션 없음 slug={args.slug}")
                return
            action = "unassign" if args.unassign else "assign"
            print(
                f"[assign_collection] (dry-run) action={action} slug={args.slug} "
                f"target_ids={args.movie_ids} (실 UPDATE 없음)"
            )
            return

        if args.unassign:
            result = await repo.unassign_movies(args.slug, args.movie_ids)
        else:
            result = await repo.assign_movies(args.slug, args.movie_ids)

        if result is None:
            print(f"[assign_collection] 실패 — 컬렉션 없음 slug={args.slug}")
            sys.exit(1)

        action = "unassign" if args.unassign else "assign"
        print(
            f"[assign_collection] {action} 완료 slug={result.collection_slug} "
            f"affected={result.affected} skipped_ids={result.skipped_ids} "
            f"moved_from_other_collection={result.moved_from_other_collection}"
        )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
