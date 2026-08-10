"""TMDB(해외)+KOFIC(한국) 대량 영화 수집 배치 — 하루 페이지 단위 점진 적재.

재시작 안전: MoviesPgRepository.upsert_movie가 slug(tmdb-{id}/kofic-{movieCd})
기준 idempotent라 같은 페이지를 다시 돌려도 중복이 안 생긴다. 중단되면 마지막
줄에 찍힌 "재시작하려면: --start-page N"을 그대로 다음 실행에 넘기면 이어받는다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/bulk_import_movies.py \
      --source tmdb_discover --country KR --pages 50
  docker compose exec backend python scripts/bulk_import_movies.py \
      --source tmdb_popular --pages 20 --start-page 21
  docker compose exec backend python scripts/bulk_import_movies.py \
      --source kofic --country KR --pages 30

  --source        tmdb_popular | tmdb_discover | kofic
  --country       KR | US | ALL (kofic은 K/F 2분류만 지원 — US는 F로 매핑)
  --pages N       이번 실행에서 처리할 페이지 수
  --start-page N  이어받을 시작 페이지(기본 1)
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
logger = logging.getLogger("bulk_import_movies")

_SOURCES = ("tmdb_popular", "tmdb_discover", "kofic")
_TMDB_SLEEP_SECONDS = 0.25
_KOFIC_NATION_CD = {"KR": "K", "US": "F"}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=_SOURCES, required=True)
    parser.add_argument("--country", choices=("KR", "US", "ALL"), default="ALL")
    parser.add_argument("--pages", type=int, required=True, help="이번 실행에서 처리할 페이지 수")
    parser.add_argument("--start-page", type=int, default=1, help="이어받을 시작 페이지")
    return parser.parse_args(argv)


def _hub_content(overview: str, genres: list[str], cast: list[str]) -> str:
    lines = [overview]
    if genres:
        lines.append(f"장르: {', '.join(genres)}")
    if cast:
        lines.append(f"출연: {', '.join(cast)}")
    return "\n".join(line for line in lines if line)


async def _ingest_tmdb_movie(
    snap, movies_repo, hub_rag, credits_interactor, session
) -> tuple[str, int, int]:
    """반환값: (outcome, skipped_cast, skipped_directors).

    outcome은 'succeeded' | 'failed' — 실패해도 이 영화만 건너뛰고 배치는
    계속된다. skipped_cast/skipped_directors는 영화 자체는 succeeded여도
    credits 백필 중 개별 cast/director가 스킵된 건수(`_backfill_one()`이
    2026-08-05부터 이 카운트를 노출 — VARCHAR(50) truncation 등으로 캐스트
    1명이 실패해도 나머지가 통째로 스킵되지 않게 된 것과 짝을 이루는 지표).
    credits 백필 자체가 통째로 실패(fetch_credits 등)하면 0, 0을 반환한다 —
    그 경우는 아래 credits except에서 별도로 로그된다.
    """
    from mova.app.dtos.studio_import_dto import MovieUpsertCommand

    try:
        movie_id = await movies_repo.upsert_movie(
            MovieUpsertCommand(
                slug=snap.slug,
                title=snap.title,
                release_year=snap.release_year,
                rating=snap.rating,
                poster_url=snap.poster_url,
                genres=snap.genres,
                synopsis=snap.overview,
                original_language=snap.original_language,
                origin_country=snap.origin_country,
            )
        )
    except Exception:
        logger.warning("[bulk_import] upsert_movie 실패 | slug=%s", snap.slug, exc_info=True)
        # DB 예외(flush 실패 등)는 세션을 pending-rollback 상태로 남긴다 — 롤백
        # 안 하면 이 세션을 계속 쓰는 이후 모든 영화가 PendingRollbackError로
        # 도미노 실패한다(실측: characters.character_name VARCHAR(50) 초과 1건이
        # 세션을 오염시켜 이후 418건이 전부 이 도미노로 실패). 한 영화 실패가
        # 배치 전체를 막지 않는다는 이 스크립트의 설계 의도를 지키려면 필수.
        await session.rollback()
        return "failed", 0, 0

    skipped_cast = 0
    skipped_directors = 0
    try:
        # CreditsBackfillInteractor의 배치 진입점(backfill_credits)은 매번 전체
        # movies를 재스캔한다 — 방금 upsert한 영화 하나만 채우면 되므로 영화당
        # 처리 메서드(_backfill_one)를 직접 재사용한다(scripts/ 스크립트에서
        # _ingest_to_hub를 직접 부르는 것과 동일한 패턴).
        one_result = await credits_interactor._backfill_one(
            movie_id, snap.tmdb_id, snap.slug, dry_run=False
        )
        skipped_cast = one_result.skipped_cast
        skipped_directors = one_result.skipped_directors
    except Exception:
        logger.warning(
            "[bulk_import] credits 백필 실패(카탈로그는 유지) | slug=%s", snap.slug, exc_info=True
        )
        await session.rollback()
    await asyncio.sleep(_TMDB_SLEEP_SECONDS)

    from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand

    try:
        await hub_rag.ingest_movie(
            HubKnowledgeUpsertCommand(
                source="mova_movie",
                # source_ref는 반드시 movie.id — 채팅이 이 값을 movie_id로 int() 파싱해
                # 후보 집합을 만든다(chat_reply.enrich_from_db). slug를 넣으면 파싱이
                # 조용히 실패해 추천이 전부 드롭된다.
                source_ref=str(movie_id),
                title=snap.title,
                content=_hub_content(snap.overview, snap.genres, snap.cast),
            )
        )
        await session.commit()
    except Exception:
        # **지우지 말 것.** 2026-08-05 배치 1000편에서 한 번도 안 걸려 "죽은 코드"로
        # 백로그에 올랐지만, 2026-08-10 재조사 결과 죽은 게 아니라 **아직 도달을
        # 못 한** 코드다 — `HubRagInteractor.ingest_movie()`가 삼키는 건 임베딩
        # 실패(`HubRagError`)뿐이고, 그 뒤 `repository.upsert()`
        # (INSERT ... ON CONFLICT, `source_ref` UNIQUE)는 try 밖이라 DB 오류는
        # 그대로 올라온다. EC2에서 임베딩이 매번 먼저 실패해 upsert까지 간 적이
        # 없었을 뿐이다. 임베딩이 실제로 도는 순간 이 rollback이 살아나며,
        # 없으면 세션이 pending-rollback으로 남아 이후 전 항목이 도미노로
        # 실패한다(1건이 418건을 죽인 선례 — .claude/rules/orm-columns.md §5).
        logger.warning(
            "[bulk_import] hub_knowledge 인제스트 실패 | slug=%s", snap.slug, exc_info=True
        )
        await session.rollback()

    return "succeeded", skipped_cast, skipped_directors


async def _ingest_kofic_movie(row: dict, movies_repo, hub_rag, session) -> str:
    """KOFIC은 tmdb_person_id가 없어 actors/characters/movie_directors 백필 대상 밖 —
    movies + hub_knowledge까지만 채운다.

    반환값: 'succeeded' | 'failed' | 'skipped'.
    """
    from mova.app.dtos.studio_import_dto import MovieUpsertCommand

    movie_cd = str(row.get("movieCd") or "").strip()
    title = str(row.get("movieNm") or "").strip()
    if not movie_cd or not title:
        return "skipped"

    slug = f"kofic-{movie_cd}"
    prdt_year_raw = str(row.get("prdtYear") or "").strip()
    release_year = int(prdt_year_raw) if prdt_year_raw.isdigit() else 0
    genres = [g.strip() for g in str(row.get("genreAlt") or "").split(",") if g.strip()]
    directors = [
        str(d.get("peopleNm") or "").strip()
        for d in (row.get("directors") or [])
        if d.get("peopleNm")
    ]

    try:
        movie_id = await movies_repo.upsert_movie(
            MovieUpsertCommand(
                slug=slug,
                title=title,
                release_year=release_year,
                rating=0.0,
                poster_url="",
                genres=genres,
            )
        )
    except Exception:
        logger.warning("[bulk_import] upsert_movie 실패 | slug=%s", slug, exc_info=True)
        # 세션 오염 방지 — _ingest_tmdb_movie와 동일한 근본 원인(도미노 실패) 대응.
        await session.rollback()
        return "failed"

    from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand

    content_lines = []
    if genres:
        content_lines.append(f"장르: {', '.join(genres)}")
    if directors:
        content_lines.append(f"감독: {', '.join(directors)}")
    if release_year:
        content_lines.append(f"제작연도: {release_year}")

    try:
        await hub_rag.ingest_movie(
            HubKnowledgeUpsertCommand(
                source="mova_movie",
                source_ref=str(movie_id),  # movie.id 고정 — 위 TMDB 경로와 같은 이유
                title=title,
                content="\n".join(content_lines),
            )
        )
        await session.commit()
    except Exception:
        logger.warning("[bulk_import] hub_knowledge 인제스트 실패 | slug=%s", slug, exc_info=True)
        await session.rollback()

    return "succeeded"


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.http.kofic_adapter import KoficAdapter, KoficAdapterError
    from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapterError
    from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
    from mova.adapter.outbound.pg.studio_actors_pg_repository import ActorsPgRepository
    from mova.adapter.outbound.pg.studio_characters_pg_repository import CharactersPgRepository
    from mova.adapter.outbound.pg.studio_movie_directors_pg_repository import (
        MovieDirectorsPgRepository,
    )
    from mova.app.use_cases.credits_backfill_interactor import CreditsBackfillInteractor
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    keymaker = get_keymaker()
    factory = get_mova_session_factory()

    stats = {
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "skipped_cast": 0,
        "skipped_directors": 0,
    }
    last_page = args.start_page - 1

    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        hub_rag = HubRagInteractor(
            repository=HubKnowledgeRepository(session), embedding=OllamaEmbeddingAdapter()
        )

        if args.source in ("tmdb_popular", "tmdb_discover"):
            catalog = TmdbCatalogAdapter(keymaker.tmdb_api_key)
            credits_interactor = CreditsBackfillInteractor(
                movies=movies_repo,
                catalog=catalog,
                actors=ActorsPgRepository(session),
                characters=CharactersPgRepository(session),
                directors=MovieDirectorsPgRepository(session),
            )
            origin = None if args.country == "ALL" else args.country

            for page in range(args.start_page, args.start_page + args.pages):
                try:
                    if args.source == "tmdb_popular":
                        snapshots = await catalog.fetch_popular(page=page)
                    else:
                        snapshots = await catalog.fetch_discover(
                            page=page, with_origin_country=origin
                        )
                except TmdbAdapterError as e:
                    logger.error("[bulk_import] page=%d TMDB fetch 실패, 배치 중단 — %s", page, e)
                    break

                if not snapshots:
                    print(f"[bulk_import] page={page} 결과 없음 — 종료")
                    last_page = page
                    break

                for snap in snapshots:
                    outcome, skipped_cast, skipped_directors = await _ingest_tmdb_movie(
                        snap, movies_repo, hub_rag, credits_interactor, session
                    )
                    stats[outcome] += 1
                    stats["skipped_cast"] += skipped_cast
                    stats["skipped_directors"] += skipped_directors

                last_page = page
                print(
                    f"[bulk_import] page={page} 처리 완료 (누적 "
                    f"succeeded={stats['succeeded']} failed={stats['failed']} "
                    f"skipped={stats['skipped']} skipped_cast={stats['skipped_cast']} "
                    f"skipped_directors={stats['skipped_directors']})"
                )
                await asyncio.sleep(_TMDB_SLEEP_SECONDS)

        else:  # kofic
            if not keymaker.kofic_api_key:
                print("[bulk_import] KOFIC_API_KEY 미설정 — kofic 소스 스킵")
                return
            kofic = KoficAdapter(keymaker.kofic_api_key)
            rep_nation_cd = _KOFIC_NATION_CD.get(args.country)

            for page in range(args.start_page, args.start_page + args.pages):
                try:
                    rows = await kofic.fetch_movie_list(
                        page=page, item_per_page=100, rep_nation_cd=rep_nation_cd
                    )
                except KoficAdapterError as e:
                    logger.error("[bulk_import] page=%d KOFIC fetch 실패, 배치 중단 — %s", page, e)
                    break

                if not rows:
                    print(f"[bulk_import] page={page} 결과 없음 — 종료")
                    last_page = page
                    break

                for row in rows:
                    outcome = await _ingest_kofic_movie(row, movies_repo, hub_rag, session)
                    stats[outcome] += 1

                last_page = page
                print(
                    f"[bulk_import] page={page} 처리 완료 (누적 "
                    f"succeeded={stats['succeeded']} failed={stats['failed']} "
                    f"skipped={stats['skipped']})"
                )

    print(
        f"[bulk_import] 완료 source={args.source} country={args.country} "
        f"succeeded={stats['succeeded']} failed={stats['failed']} skipped={stats['skipped']} "
        f"skipped_cast={stats['skipped_cast']} skipped_directors={stats['skipped_directors']} "
        f"last_page={last_page}"
    )
    print(f"[bulk_import] 재시작하려면: --start-page {last_page + 1}")


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
