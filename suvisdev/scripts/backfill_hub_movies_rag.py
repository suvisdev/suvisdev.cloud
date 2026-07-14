"""mova_movie_dataset.jsonl → ontology Hub(hub_knowledge) RAG 색인 1회 백필.

source_ref(slug) 기준 upsert라 여러 번 실행해도 안전하다(멱등). 이후 신규/갱신 영화는
mova/app/use_cases/import_interactor.py의 TMDB/KOFIC 임포트 훅이 자동으로 반영한다.

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
    from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    reload_env()
    await create_tables()  # hub_knowledge 테이블 없으면 생성

    factory = get_mova_session_factory()
    embedding = OllamaEmbeddingAdapter()

    rows = [json.loads(line) for line in _DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"[backfill] {len(rows)}편 로드: {_DATASET}")

    ingested = 0
    async with factory() as session:
        hub_rag = HubRagInteractor(
            repository=HubKnowledgeRepository(session=session), embedding=embedding
        )
        for row in rows:
            slug = str(row.get("slug") or "")
            title = str(row.get("title") or "")
            if not slug or not title:
                continue
            await hub_rag.ingest_movie(
                HubKnowledgeUpsertCommand(
                    source="mova_movie",
                    source_ref=slug,
                    title=title,
                    content=_content(row),
                )
            )
            ingested += 1
            print(f"[backfill] {ingested}/{len(rows)} {slug}")
        await session.commit()

    print(f"[backfill] 완료: {ingested}편 색인")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
