"""RAG Hub DI — Spoke(mova 등)가 Depends로 직접 끌어다 쓴다."""

from __future__ import annotations

import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from ontology.adapter.outbound.llm.gemini_embedding_adapter import GeminiEmbeddingAdapter
from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
    HubKnowledgeRepository,
)
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort
from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor


def get_hub_knowledge_repository(
    db: AsyncSession = Depends(get_db),
) -> HubKnowledgePort:
    return HubKnowledgeRepository(session=db)


def get_hub_embedding_port() -> EmbeddingPort:
    """`EMBEDDING_BACKEND`로 임베딩 백엔드를 고른다 (기본 `ollama` — 집 GPU 환경).

    Ollama 없는 배포 환경에선 `gemini`로 오버라이드해야 한다 — 안 하면 쿼리 임베딩이
    매번 실패해 벡터 검색 경로 전체가 조용히 죽고 태그 키워드 폴백만 돈다
    (2026-08-07 실측으로 확인된 프로덕션 상태). **백엔드를 바꾸면 저장된
    벡터와 의미 공간이 달라지므로 hub_knowledge 재임베딩이 필수다.**
    """
    if os.getenv("EMBEDDING_BACKEND", "ollama").strip().lower() == "gemini":
        return GeminiEmbeddingAdapter()
    return OllamaEmbeddingAdapter()


def get_hub_rag_use_case(
    repository: HubKnowledgePort = Depends(get_hub_knowledge_repository),
    embedding: EmbeddingPort = Depends(get_hub_embedding_port),
) -> HubRagUseCase:
    return HubRagInteractor(repository=repository, embedding=embedding)
