"""시맨틱 인텐트 게이트웨이 — POST /ontology/semantic/ask.

질문 1건을 crud/rag/general 세 갈래로 분류해 처리한다. 분류·RAG 답변은 로컬
Qwen2.5-1.5B(Ollama)가 시스템 프롬프트만 바꿔가며 겸한다 — QLoRA 파인튜닝은
필요 없다(PoC 단계 프롬프트 튜닝으로 충분, 실제 판단 로직은
semantic_router_interactor.py 참고).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ontology.adapter.inbound.api.schemas.semantic_router_schema import (
    SemanticAskSchema,
    SemanticRouteResponseSchema,
)
from ontology.app.dtos.semantic_router_dto import SemanticRouteCommand
from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.dependencies.semantic_router_provider import get_semantic_router_use_case

semantic_router = APIRouter(prefix="/semantic", tags=["ontology-semantic"])


@semantic_router.post("/ask", response_model=SemanticRouteResponseSchema)
async def ask(
    req: SemanticAskSchema,
    router: SemanticRouterUseCase = Depends(get_semantic_router_use_case),
) -> SemanticRouteResponseSchema:
    dto = await router.route(SemanticRouteCommand.from_schema(req))
    return dto.to_schema()
