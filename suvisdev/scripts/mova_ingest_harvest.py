"""harvester JSONL 산출물 → mova RAG(hub_knowledge) 적재.

harvester(apps/ontology) 코드는 일절 import하지 않는다 — JSONL 파일 포맷만을
계약으로 삼는다. 원래 요청 형태(python -m apps.mova ingest-harvest)는 이 저장소의
sys.path 구조와 맞지 않아 harvester_cli.py와 같은 방식으로 조정했다.

Usage (suvisdev 폴더에서):
  python scripts/mova_ingest_harvest.py apps/ontology/resources/crawled/kowiki_20260716.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


async def main(jsonl_path: Path) -> None:
    from core.matrix.grid_oracle_database_manager import (
        create_tables,
        dispose_engine,
        get_mova_session_factory,
        reload_env,
    )
    from mova.adapter.outbound.harvest.harvest_jsonl_reader import HarvestJsonlReaderAdapter
    from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
    from mova.app.use_cases.harvest_ingest_interactor import HarvestIngestInteractor
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    reload_env()
    await create_tables()

    factory = get_mova_session_factory()
    async with factory() as session:
        interactor = HarvestIngestInteractor(
            reader=HarvestJsonlReaderAdapter(),
            movies=MoviesPgRepository(session=session),
            hub_rag=HubRagInteractor(
                repository=HubKnowledgeRepository(session=session),
                embedding=OllamaEmbeddingAdapter(),
            ),
        )
        result = await interactor.ingest(jsonl_path)
        await session.commit()

    print(
        f"[ingest-harvest] {jsonl_path} 완료 | "
        f"total={result.total} ingested={result.ingested} "
        f"matched={result.matched} unmatched={result.unmatched}"
    )
    await dispose_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", type=Path)
    args = parser.parse_args()
    asyncio.run(main(args.jsonl_path))
