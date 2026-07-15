from __future__ import annotations

import logging

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto, HubKnowledgeUpsertCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort

logger = logging.getLogger(__name__)


class HubRagInteractor(HubRagUseCase):
    def __init__(self, *, repository: HubKnowledgePort, embedding: EmbeddingPort) -> None:
        self._repository = repository
        self._embedding = embedding

    async def ingest_movie(self, command: HubKnowledgeUpsertCommand) -> None:
        text = f"{command.title}\n{command.content}".strip()
        if not text:
            return
        try:
            vector = await self._embedding.embed(text)
        except HubRagError as e:
            # 임베딩 실패해도 임포트 자체(Spoke 쪽 트랜잭션)는 막지 않는다 — dispatch의
            # _embed_or_none과 동일 원칙: RAG 색인은 부가 기능이지 원본 데이터 유실 사유가 아니다.
            logger.warning(
                "[HubRagInteractor] ingest 임베딩 실패, 색인 생략 | source_ref=%s detail=%s",
                command.source_ref,
                e.detail,
            )
            return
        await self._repository.upsert(command, vector)
        logger.info(
            "[HubRagInteractor] ingest 완료 | source=%s source_ref=%s dim=%d",
            command.source,
            command.source_ref,
            len(vector),
        )

    async def search_movies(
        self, query: str, *, k: int = 8, trace_id: str = ""
    ) -> list[HubKnowledgeHitDto]:
        if not query.strip():
            return []
        try:
            vector = await self._embedding.embed(query)
        except HubRagError as e:
            logger.warning(
                "[HubRagInteractor] trace=%s embed 실패, 검색 생략 | detail=%s", trace_id, e.detail
            )
            return []
        logger.info("[HubRagInteractor] trace=%s embed 완료 dim=%d", trace_id, len(vector))

        hits = await self._repository.search(vector, k=k, source="mova_movie")
        top1 = hits[0].title if hits else "(없음)"
        top1_score = hits[0].score if hits else 0.0
        logger.info(
            "[HubRagInteractor] trace=%s vector_search hits=%d top1=%s score=%.3f",
            trace_id,
            len(hits),
            top1,
            top1_score,
        )
        return hits
