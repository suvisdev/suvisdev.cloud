from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from ontology.adapter.outbound.llm.exaone_small_llm_adapter import ExaoneSmallLlmAdapter
from ontology.adapter.outbound.llm.fallback_hub_llm_adapter import FallbackHubLlmAdapter
from ontology.adapter.outbound.llm.gemini_llm_adapter import GeminiLlmAdapter
from ontology.adapter.outbound.llm.llm_intent_classifier import LlmIntentClassifier
from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
    HubKnowledgeRepository,
)
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort
from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor
from ontology.app.use_cases.Mycroft_interactor import MycroftInteractor
from ontology.app.use_cases.semantic_router_interactor import SemanticRouterInteractor
from ontology.dependencies.hub_rag_provider import get_hub_embedding_port


def get_exaone_small_llm_port() -> HubLlmPort:
    return ExaoneSmallLlmAdapter()


def get_gemini_llm_port() -> HubLlmPort:
    return GeminiLlmAdapter()


def get_intent_classifier(
    local: HubLlmPort = Depends(get_exaone_small_llm_port),
    gemini: HubLlmPort = Depends(get_gemini_llm_port),
) -> IntentClassifierPort:
    # EXAONE(Ollama)은 로컬 GPU 전용 — 없는 환경에선 분류가 전부 기본값으로 새던
    # 잠복 결함(2026-08-28 실측). Gemini 폴백을 태워 양쪽 환경에서 분류가 산다.
    return LlmIntentClassifier(llm=FallbackHubLlmAdapter(primary=local, fallback=gemini))


def get_semantic_hub_rag_use_case(
    db: AsyncSession = Depends(get_db),
) -> HubRagUseCase:
    repository: HubKnowledgePort = HubKnowledgeRepository(session=db)
    # EMBEDDING_BACKEND 분기(get_hub_embedding_port)를 재사용 — Ollama 하드코딩
    # 시 gemini 환경에서 RAG 경로가 조용히 죽는다(2026-09-11 리뷰, 08-07 실측과
    # 동일 클래스).
    return HubRagInteractor(repository=repository, embedding=get_hub_embedding_port())


def get_semantic_mycroft_use_case(
    llm: HubLlmPort = Depends(get_gemini_llm_port),
) -> MycroftUseCase:
    return MycroftInteractor(llm=llm)


def get_semantic_router_use_case(
    classifier: IntentClassifierPort = Depends(get_intent_classifier),
    router_llm: HubLlmPort = Depends(get_exaone_small_llm_port),
    rag: HubRagUseCase = Depends(get_semantic_hub_rag_use_case),
    general: MycroftUseCase = Depends(get_semantic_mycroft_use_case),
) -> SemanticRouterUseCase:
    return SemanticRouterInteractor(
        classifier=classifier, router_llm=router_llm, rag=rag, general=general
    )
