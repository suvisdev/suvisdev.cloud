"""mova_movie_dataset.jsonl → ontology Hub(hub_knowledge) RAG 색인 1회 백필.

`source_ref`(= `movie.id`) 기준 upsert라 여러 번 실행해도 안전하다(멱등). 이후
신규/갱신 영화는 mova/app/use_cases/import_interactor.py의 TMDB/KOFIC 임포트 훅이
자동으로 반영한다.

JSONL은 slug만 갖고 있으므로 DB에서 slug→movie.id를 조회해 색인한다 —
`source_ref`에 slug를 넣으면 채팅이 이 값을 movie_id로 int() 파싱하는 단계
(chat_reply.enrich_from_db)에서 조용히 실패해 추천이 전부 드롭된다.
카탈로그에 없는 slug는 건너뛴다(그 영화를 색인해도 추천에 못 실린다).

Usage (suvisdev 폴더에서):
  python scripts/backfill_hub_movies_rag.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for p in (_BACKEND, _APPS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

_DATASET = _APPS / "mova" / "_docs" / "mova_movie_dataset.jsonl"


def _content(row: dict) -> str:
    lines = [str(row.get("overview") or "")]
    genres = row.get("genres") or []
    if genres:
        lines.append(f"장르: {', '.join(genres)}")
    cast = [c.get("actor_name", "") for c in (row.get("cast") or []) if c.get("actor_name")]
    if cast:
        lines.append(f"출연: {', '.join(cast[:5])}")
    return "\n".join(line for line in lines if line)


async def main() -> None:
    from core.matrix.grid_oracle_database_manager import (
        create_tables,
        dispose_engine,
        get_mova_session_factory,
        reload_env,
    )
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
    from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    reload_env()
    await create_tables()  # hub_knowledge 테이블 없으면 생성

    factory = get_mova_session_factory()
    embedding = OllamaEmbeddingAdapter()

    rows = [json.loads(line) for line in _DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"[backfill] {len(rows)}편 로드: {_DATASET}")

    ingested = 0
    skipped = 0
    async with factory() as session:
        hub_rag = HubRagInteractor(
            repository=HubKnowledgeRepository(session=session), embedding=embedding
        )
        movies_repo = MoviesPgRepository(session)
        ids_by_slug = {slug: movie_id for movie_id, slug in await movies_repo.list_all_slugs()}

        for row in rows:
            slug = str(row.get("slug") or "")
            title = str(row.get("title") or "")
            if not slug or not title:
                skipped += 1
                continue
            movie_id = ids_by_slug.get(slug)
            if movie_id is None:
                print(f"[backfill] 카탈로그에 없는 slug, 스킵: {slug}")
                skipped += 1
                continue
            await hub_rag.ingest_movie(
                HubKnowledgeUpsertCommand(
                    source="mova_movie",
                    source_ref=str(movie_id),
                    title=title,
                    content=_content(row),
                )
            )
            ingested += 1
            print(f"[backfill] {ingested}/{len(rows)} {slug} -> movie_id={movie_id}")
        await session.commit()

    # ingest_movie()는 임베딩 실패를 내부에서 삼키고 정상 반환한다 — 이 수치는
    # "색인 시도"이지 "임베딩까지 성공"이 아니다. 실제 반영 건수는 DB에서 확인할 것
    # (select count(*) from hub_knowledge where source='mova_movie' and embedding is not null).
    print(f"[backfill] 완료: 시도 {ingested}편 / 스킵 {skipped}편")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
