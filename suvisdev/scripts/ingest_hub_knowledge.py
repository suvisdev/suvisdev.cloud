"""movies 카탈로그를 hub_knowledge(ontology RAG 지식 저장소)에 수동 인제스트.

seed_catalog_if_sparse는 movies >= 5편이면 스킵되므로, 이미 채워진 로컬
카탈로그의 hub_knowledge만 비어있는 경우 이 스크립트로 별도 채운다.

Usage (suvisdev 폴더에서):
  docker compose exec backend python scripts/ingest_hub_knowledge.py
  (로컬 실행 시) python scripts/ingest_hub_knowledge.py
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

from sqlalchemy import select  # noqa: E402

from core.matrix.grid_oracle_database_manager import get_mova_session_factory  # noqa: E402
from mova.adapter.outbound.orm.studio_actors_orm import MovaActor  # noqa: E402
from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector  # noqa: E402
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository  # noqa: E402
from mova.adapter.outbound.pg.studio_characters_pg_repository import (  # noqa: E402
    CharactersPgRepository,
)
from mova.app.dtos.studio_movies_dto import MovieFilterQuery  # noqa: E402
from ontology.adapter.outbound.llm.ollama_embedding_adapter import (  # noqa: E402
    OllamaEmbeddingAdapter,
)
from ontology.adapter.outbound.repositories.hub_knowledge_repository import (  # noqa: E402
    HubKnowledgeRepository,
)
from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand  # noqa: E402
from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor  # noqa: E402


async def _director_names(session, movie_id: int) -> list[str]:
    rows = await session.execute(
        select(MovaActor.name)
        .join(MovaMovieDirector, MovaMovieDirector.actor_id == MovaActor.id)
        .where(MovaMovieDirector.movie_id == movie_id)
    )
    return [name for (name,) in rows.all()]


async def main() -> None:
    factory = get_mova_session_factory()
    async with factory() as session:
        movies_repo = MoviesPgRepository(session)
        chars_repo = CharactersPgRepository(session)
        hub = HubRagInteractor(
            repository=HubKnowledgeRepository(session),
            embedding=OllamaEmbeddingAdapter(),
        )

        listing = await movies_repo.list_movies(MovieFilterQuery(limit=100))
        movies = listing.items
        print(f"총 {len(movies)}편 인제스트 시작")

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
                succeeded += 1
                print(f"  완료: {movie.title}")
            except Exception as e:  # noqa: BLE001
                print(f"  실패: {movie.title} — {e}")

        await session.commit()
        print(f"전체 완료 succeeded={succeeded}/{len(movies)}")


if __name__ == "__main__":
    asyncio.run(main())
