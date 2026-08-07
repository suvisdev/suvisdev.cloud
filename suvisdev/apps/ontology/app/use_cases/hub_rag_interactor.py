from __future__ import annotations

import logging

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto, HubKnowledgeUpsertCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort

logger = logging.getLogger(__name__)

# 코사인 유사도 하한. 이보다 낮은 히트는 "검색 결과"가 아니라 잡음으로 보고 버린다.
#
# 2026-08-07 사고: `EMBEDDING_BACKEND`를 gemini로 바꾸면서 hub_knowledge에 저장된
# nomic-embed-text 벡터를 재임베딩하지 않아, 서로 다른 의미 공간을 비교하게 됐다.
# 차원이 768로 같아 에러도 안 나고, 유사도 0.04짜리 무작위 이웃 8건이 "정상 히트"로
# 반환돼 **정상 동작하던 태그 검색 경로를 통째로 대체**했다(추천 품질 붕괴).
# 임계값을 두면 이런 불일치가 조용히 오염시키는 대신 빈 결과 → 태그 폴백으로 떨어진다.
# 0.15는 관측된 잡음(0.04)보다 충분히 높고 정상 매칭(통상 0.5+)보다 충분히 낮다.
_MIN_HIT_SCORE = 0.15


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

        raw_hits = await self._repository.search(vector, k=k, source="mova_movie")
        hits = [h for h in raw_hits if h.score >= _MIN_HIT_SCORE]
        top1 = raw_hits[0].title if raw_hits else "(없음)"
        top1_score = raw_hits[0].score if raw_hits else 0.0
        logger.info(
            "[HubRagInteractor] trace=%s vector_search hits=%d(raw %d) top1=%s score=%.3f",
            trace_id,
            len(hits),
            len(raw_hits),
            top1,
            top1_score,
        )
        if raw_hits and not hits:
            logger.warning(
                "[HubRagInteractor] trace=%s 유사도 전부 %.2f 미만 — 잡음으로 보고 폐기. "
                "임베딩 백엔드와 저장된 벡터의 의미 공간이 다를 수 있다(재임베딩 필요).",
                trace_id,
                _MIN_HIT_SCORE,
            )
        return hits
