"""movies 카탈로그를 hub_knowledge(ontology RAG 지식 저장소)에 수동 인제스트.

seed_catalog_if_sparse는 movies >= 5편이면 스킵되므로, 이미 채워진 로컬
카탈로그의 hub_knowledge만 비어있는 경우 이 스크립트로 별도 채운다.

Usage (suvisdev 폴더에서):
  kubectl -n suvisdev exec deploy/backend -- python scripts/ingest_hub_knowledge.py
  (로컬 실행 시) python scripts/ingest_hub_knowledge.py

  --embedding-backend {ollama,gemini}
      임베딩 백엔드. 미지정 시 `EMBEDDING_BACKEND` 환경변수(기본 ollama)를 따른다.
  --reset
      시작 전에 기존 `source='mova_movie'` 로우를 전부 삭제한다.
      **백엔드를 바꿀 땐 필수** — Ollama(nomic-embed-text)와 Gemini는 의미
      공간이 달라, 두 벡터가 한 테이블에 섞이면 코사인 거리 비교가 무의미해져
      검색 결과가 조용히 망가진다(차원은 768로 같아서 에러도 안 난다).
  --limit N
      앞 N편만 처리(시험 실행용).
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

from sqlalchemy import delete, select  # noqa: E402

from core.matrix.grid_oracle_database_manager import get_mova_session_factory  # noqa: E402
from mova.adapter.outbound.orm.studio_actors_orm import MovaActor  # noqa: E402
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector  # noqa: E402
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository  # noqa: E402
from mova.adapter.outbound.pg.studio_characters_pg_repository import (  # noqa: E402
    CharactersPgRepository,
)
from mova.app.dtos.studio_movies_dto import MovieFilterQuery  # noqa: E402
from ontology.adapter.outbound.llm.gemini_embedding_adapter import (  # noqa: E402
    GeminiEmbeddingAdapter,
)
from ontology.adapter.outbound.llm.ollama_embedding_adapter import (  # noqa: E402
    OllamaEmbeddingAdapter,
)
from ontology.adapter.outbound.orm.hub_knowledge_orm import HubKnowledgeOrm  # noqa: E402
from ontology.adapter.outbound.repositories.hub_knowledge_repository import (  # noqa: E402
    HubKnowledgeRepository,
)
from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand  # noqa: E402
from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--embedding-backend",
        choices=("ollama", "gemini"),
        default=os.getenv("EMBEDDING_BACKEND", "ollama").strip().lower(),
    )
    parser.add_argument(
        "--reset", action="store_true", help="기존 mova_movie 로우 전량 삭제 후 인제스트"
    )
    parser.add_argument("--limit", type=int, default=None, help="앞 N편만 처리(시험 실행용)")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="이미 색인된 source_ref는 건너뜀 — 중단·부분 실패 후 이어서 실행용",
    )
    return parser.parse_args(argv)


def _build_embedding(backend: str):
    return GeminiEmbeddingAdapter() if backend == "gemini" else OllamaEmbeddingAdapter()


async def _director_names(session, movie_id: int) -> list[str]:
    rows = await session.execute(
        select(MovaActor.name)
        .join(MovaMovieDirector, MovaMovieDirector.actor_id == MovaActor.id)
        .where(MovaMovieDirector.movie_id == movie_id)
    )
    return [name for (name,) in rows.all()]


async def main(args: argparse.Namespace) -> None:
    # 대량 재임베딩도 크론 백필과 같은 이유로 별도 키 사용(2026-08-28 쿼터 분리)
    # — backfill_movie_embeddings_cli.py 주석 참고. 미설정이면 기존 키 그대로.
    backfill_key = os.getenv("GEMINI_BACKFILL_API_KEY", "").strip()
    backfill_client = None
    if backfill_key:
        from google import genai

        backfill_client = genai.Client(api_key=backfill_key)

    def _build_embed():
        if args.embedding_backend == "gemini":
            return (
                GeminiEmbeddingAdapter(client=backfill_client)
                if backfill_client
                else GeminiEmbeddingAdapter()
            )
        return OllamaEmbeddingAdapter()

    factory = get_mova_session_factory()
    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        chars_repo = CharactersPgRepository(session)
        hub = HubRagInteractor(
            repository=HubKnowledgeRepository(session),
            embedding=_build_embed(),
        )

        if args.reset:
            result = await session.execute(
                delete(HubKnowledgeOrm).where(HubKnowledgeOrm.source == "mova_movie")
            )
            await session.commit()
            print(f"[reset] 기존 mova_movie 로우 {result.rowcount}건 삭제")

        movies = []
        page_size = 200
        offset = 0
        while True:
            listing = await movies_repo.list_movies(
                MovieFilterQuery(limit=page_size, offset=offset)
            )
            movies.extend(listing.items)
            if len(listing.items) < page_size:
                break
            offset += page_size
        if args.limit is not None:
            movies = movies[: args.limit]
        print(f"백엔드={args.embedding_backend} 총 {len(movies)}편 인제스트 시작")

        # --skip-existing: 이미 색인된 영화는 건너뛴다 — 중단·부분 실패 후 재실행용.
        existing_refs: set[str] = set()
        if args.skip_existing:
            rows = await session.execute(
                select(HubKnowledgeOrm.source_ref).where(HubKnowledgeOrm.source == "mova_movie")
            )
            existing_refs = {r[0] for r in rows}
            print(f"[skip-existing] 기존 색인 {len(existing_refs)}건은 건너뜀")

        succeeded = 0
        skipped = 0
        failed: list[str] = []
        for movie in movies:
            if str(movie.id) in existing_refs:
                skipped += 1
                continue
            cast = await chars_repo.get_cast_by_movie(movie.id)
            cast_names = ", ".join(c.actor_name for c in cast.cast[:5])
            director_names = ", ".join(await _director_names(session, movie.id))

            content_lines = [f"개봉: {movie.release_year}"]
            if movie.genres:
                content_lines.append(f"장르: {', '.join(movie.genres)}")
            if cast_names:
                content_lines.append(f"출연: {cast_names}")
            if director_names:
                content_lines.append(f"감독: {director_names}")
            content = "\n".join(content_lines)

            command = HubKnowledgeUpsertCommand(
                source="mova_movie",
                source_ref=str(movie.id),
                title=movie.title,
                content=content,
            )
            try:
                # ingest_movie는 임베딩 실패(레이트리밋 등)를 예외 대신 False로
                # 돌려준다 — 지수 백오프로 재시도한다(2026-08-26: 전량 실행에서
                # 2,083건이 조용히 생략돼 "성공 2,972"로 위장된 사고의 재발 방지).
                indexed = False
                for attempt in range(5):
                    indexed = await hub.ingest_movie(command)
                    if indexed:
                        break
                    await asyncio.sleep(2 * (2**attempt))  # 2,4,8,16,32초
                await session.commit()
                if indexed:
                    succeeded += 1
                    print(f"  완료: {movie.title}")
                else:
                    failed.append(movie.title)
                    print(f"  실패(재시도 소진): {movie.title}")
            except Exception as e:  # noqa: BLE001
                await session.rollback()
                failed.append(movie.title)
                print(f"  실패: {movie.title} — {e}")

        print(
            f"전체 완료 succeeded={succeeded} skipped={skipped} "
            f"failed={len(failed)} / {len(movies)}"
        )
        if failed:
            print("실패 목록(앞 20): " + ", ".join(failed[:20]))


if __name__ == "__main__":
    asyncio.run(main(_parse_args()))
