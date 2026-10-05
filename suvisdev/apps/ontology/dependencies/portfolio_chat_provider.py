"""홈 포트폴리오 채팅 DI — 임베딩·지식 저장소는 hub_rag_provider 것을 그대로 쓴다."""

from __future__ import annotations

import os

from fastapi import Depends

from ontology.adapter.outbound.llm.exaone_llm_adapter import ExaoneLlmAdapter
from ontology.adapter.outbound.llm.fallback_hub_llm_adapter import FallbackHubLlmAdapter
from ontology.adapter.outbound.llm.gemini_llm_adapter import GeminiLlmAdapter
from ontology.adapter.outbound.llm.retry_hub_llm_adapter import RetryHubLlmAdapter
from ontology.app.ports.input.portfolio_chat_use_case import PortfolioChatUseCase
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort
from ontology.app.use_cases.portfolio_chat_interactor import PortfolioChatInteractor
from ontology.dependencies.hub_rag_provider import (
    get_hub_embedding_port,
    get_hub_knowledge_repository,
)


def get_portfolio_llm_port() -> HubLlmPort:
    """`PORTFOLIO_LLM_BACKEND` — exaone(기본): 로컬 7.8B, 실패 시 Gemini 폴백 / gemini: Gemini.

    Gemini는 일시 오류(429·502·503·504)면 한 번 더 부른다(2026-10-06, 'high demand' 503 실측).
    gemini 모드에서 `PORTFOLIO_LLM_FALLBACK_URL`(올라마 주소)이 있으면 Gemini가 끝내 실패할 때 그 주소의
    EXAONE 7.8B로 답한다 — 노트북 `.env`에만 둔다(노트북 GPU). 집컴은 비워 7.8B를 올리지 않는다.
    매 호출 환경변수를 읽는다(테스트에서 patch.dict 가능해야 하므로 — hub_rag_provider와 동일).
    """
    gemini = RetryHubLlmAdapter(GeminiLlmAdapter())
    if os.getenv("PORTFOLIO_LLM_BACKEND", "exaone").strip().lower() == "gemini":
        fallback_url = os.getenv("PORTFOLIO_LLM_FALLBACK_URL", "").strip()
        if not fallback_url:
            return gemini
        return FallbackHubLlmAdapter(
            primary=gemini, fallback=ExaoneLlmAdapter(base_url=fallback_url)
        )
    return FallbackHubLlmAdapter(primary=ExaoneLlmAdapter(), fallback=gemini)


def get_portfolio_chat_use_case(
    repository: HubKnowledgePort = Depends(get_hub_knowledge_repository),
    embedding: EmbeddingPort = Depends(get_hub_embedding_port),
    llm: HubLlmPort = Depends(get_portfolio_llm_port),
) -> PortfolioChatUseCase:
    return PortfolioChatInteractor(repository=repository, embedding=embedding, llm=llm)
