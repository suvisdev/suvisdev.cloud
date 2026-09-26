"""POST /portfolio/chat — 홈 입력창의 AI 대화(무인증, IP 레이트리밋)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ontology.adapter.inbound.api.rate_limit import chat_rate_limit
from ontology.adapter.inbound.api.schemas.portfolio_chat_schema import (
    PortfolioChatRequest,
    PortfolioChatResponseSchema,
)
from ontology.app.dtos.portfolio_chat_dto import PortfolioChatCommand
from ontology.app.ports.input.portfolio_chat_use_case import PortfolioChatUseCase
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.dependencies.portfolio_chat_provider import get_portfolio_chat_use_case

logger = logging.getLogger(__name__)

# 업스트림(ollama·Gemini) 오류 원문은 로그에만 남긴다 — 09-11 보안 리뷰(502 detail 일반 문구화)와 동일.
GENERIC_ERROR_DETAIL = "AI 응답 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."

portfolio_chat_router = APIRouter(prefix="/chat", tags=["portfolio-chat"])


@portfolio_chat_router.post("", response_model=PortfolioChatResponseSchema)
async def chat(
    req: PortfolioChatRequest,
    use_case: PortfolioChatUseCase = Depends(get_portfolio_chat_use_case),
    _rate: None = Depends(chat_rate_limit),
) -> PortfolioChatResponseSchema:
    try:
        dto = await use_case.chat(PortfolioChatCommand.from_schema(req))
    except HubRagError as e:
        logger.warning(
            "[portfolio/chat] LLM/RAG 실패 | status=%s detail=%s", e.status_code, e.detail
        )
        raise HTTPException(status_code=e.status_code, detail=GENERIC_ERROR_DETAIL) from e
    return dto.to_schema()
