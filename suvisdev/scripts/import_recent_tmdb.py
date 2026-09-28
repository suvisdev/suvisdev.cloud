"""TMDB 최신 개봉작을 카탈로그에 없는 것만 N편 수집 — mova 카탈로그 규칙 적용(2026-09-28).

규칙(하나라도 어기면 건너뜀):
  - 성인물 제외: TMDB include_adult=false
  - 원어 ko·en만: ALLOWED_ORIGINAL_LANGUAGES — 그 밖은 목록·채팅에서 어차피 숨겨져 넣어도 안 보인다(08-26)
  - 포스터·한국어 줄거리 필수: 빈 껍데기 영화가 "가짜 DB"로 보였던 사고(08-13 KOFIC 986편 삭제)
  - 개봉일이 오늘 이전: 미개봉작 제외
  - 투표 수 하한(--vote-count-gte, 기본 20): 무명·저품질 배제. 가중 평점 정렬과 초성 게임 품질용
  - 중복 제외: 같은 slug(tmdb-{id}) 또는 같은 정규화 제목+연도가 이미 있으면(KOFIC 출신 동명작 포함)
적재는 bulk_import_movies._ingest_tmdb_movie를 그대로 쓴다 — movies·출연/감독·hub_knowledge(RAG) 임베딩.

Usage (파드 안, suvisdev 폴더):
  python scripts/import_recent_tmdb.py --target 500 --dry-run   # 몇 편이 새로 들어올지만
  python scripts/import_recent_tmdb.py --target 500
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
for _p in (_BACKEND, _BACKEND / "apps"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _bulk_module():
    spec = importlib.util.spec_from_file_location(
        "bulk_import_movies", _BACKEND / "scripts/bulk_import_movies.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def _run(args: argparse.Namespace) -> None:
    from sqlalchemy import select

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
    from mova.adapter.outbound.orm.studio_movies_orm import ALLOWED_ORIGINAL_LANGUAGES, MovaMovie
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
    from mova.adapter.outbound.pg.studio_actors_pg_repository import ActorsPgRepository
    from mova.adapter.outbound.pg.studio_characters_pg_repository import CharactersPgRepository
    from mova.adapter.outbound.pg.studio_movie_directors_pg_repository import (
        MovieDirectorsPgRepository,
    )
    from mova.app.use_cases.credits_backfill_interactor import CreditsBackfillInteractor
    from mova.domain.value_objects.movie_title import normalize_title
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    bulk = _bulk_module()
    today = (datetime.now(UTC) + timedelta(hours=9)).strftime("%Y-%m-%d")
    catalog = TmdbCatalogAdapter(get_keymaker().tmdb_api_key)
    factory = get_mova_session_factory()
    reasons: dict[str, int] = {}
    added: list[str] = []

    async with factory() as session:
        rows = (
            await session.execute(select(MovaMovie.slug, MovaMovie.title, MovaMovie.release_year))
        ).all()
        slugs = {r[0] for r in rows}
        title_year = {(normalize_title(r[1] or ""), r[2]) for r in rows}
        print(
            f"[recent] 기존 카탈로그 {len(rows)}편 · 목표 신규 {args.target}편 · 개봉일 ≤ {today}"
        )

        movies_repo = MoviesPgRepository(session)
        hub_rag = HubRagInteractor(
            repository=HubKnowledgeRepository(session), embedding=OllamaEmbeddingAdapter()
        )
        credits = CreditsBackfillInteractor(
            movies=movies_repo,
            catalog=catalog,
            actors=ActorsPgRepository(session),
            characters=CharactersPgRepository(session),
            directors=MovieDirectorsPgRepository(session),
        )

        def skip(reason: str) -> None:
            reasons[reason] = reasons.get(reason, 0) + 1

        for page in range(1, args.max_pages + 1):
            if len(added) >= args.target:
                break
            snaps = await catalog.fetch_discover(
                page=page,
                sort_by="primary_release_date.desc",
                vote_count_gte=args.vote_count_gte,
                release_date_lte=today,
            )
            if not snaps:
                print(f"[recent] page={page} 결과 없음 — 종료")
                break
            for snap in snaps:
                if len(added) >= args.target:
                    break
                if snap.slug in slugs:
                    skip("이미 있음(slug)")
                    continue
                key = (normalize_title(snap.title), snap.release_year)
                if key in title_year:
                    skip("이미 있음(제목+연도)")
                    continue
                if snap.original_language not in ALLOWED_ORIGINAL_LANGUAGES:
                    skip(f"원어 {snap.original_language or '?'}")
                    continue
                if not snap.poster_url:
                    skip("포스터 없음")
                    continue
                if not snap.overview.strip():
                    skip("한국어 줄거리 없음")
                    continue
                slugs.add(snap.slug)
                title_year.add(key)
                if args.dry_run:
                    added.append(f"{snap.title} ({snap.release_year})")
                    continue
                outcome, _, _ = await bulk._ingest_tmdb_movie(
                    snap, movies_repo, hub_rag, credits, session
                )
                if outcome == "succeeded":
                    added.append(f"{snap.title} ({snap.release_year})")
                else:
                    skip("적재 실패")
            print(f"[recent] page={page} 신규 누적 {len(added)}편 · 건너뜀 {reasons}", flush=True)

    mode = "(dry-run — 저장 안 함)" if args.dry_run else ""
    print(f"\n[recent] 완료{mode}: 신규 {len(added)}편 · 건너뜀 {reasons}")
    print("[recent] 예시:", ", ".join(added[:15]))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--target", type=int, default=500)
    ap.add_argument("--vote-count-gte", type=int, default=20)
    ap.add_argument("--max-pages", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    main()
