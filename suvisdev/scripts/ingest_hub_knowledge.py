"""movies 카탈로그를 hub_knowledge(ontology RAG 지식 저장소)에 수동 인제스트.

seed_catalog_if_sparse는 movies >= 5편이면 스킵되므로, 이미 채워진 로컬
카탈로그의 hub_knowledge만 비어있는 경우 이 스크립트로 별도 채운다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/ingest_hub_knowledge.py
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
    factory = get_mova_session_factory()
    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        chars_repo = CharactersPgRepository(session)
        hub = HubRagInteractor(
            repository=HubKnowledgeRepository(session),
            embedding=_build_embedding(args.embedding_backend),
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

        succeeded = 0
        for movie in movies:
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

            try:
                await hub.ingest_movie(
                    HubKnowledgeUpsertCommand(
                        source="mova_movie",
                        source_ref=str(movie.id),
                        title=movie.title,
                        content=content,
                    )
                )
                await session.commit()
                succeeded += 1
                print(f"  완료: {movie.title}")
            except Exception as e:  # noqa: BLE001
                await session.rollback()
                print(f"  실패: {movie.title} — {e}")

        print(f"전체 완료 succeeded={succeeded}/{len(movies)}")


if __name__ == "__main__":
    asyncio.run(main(_parse_args()))
