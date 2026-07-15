"""RAG Hub DI — Spoke(mova 등)가 Depends로 직접 끌어다 쓴다."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
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
    return OllamaEmbeddingAdapter()


def get_hub_rag_use_case(
    repository: HubKnowledgePort = Depends(get_hub_knowledge_repository),
    embedding: EmbeddingPort = Depends(get_hub_embedding_port),
) -> HubRagUseCase:
    return HubRagInteractor(repository=repository, embedding=embedding)
