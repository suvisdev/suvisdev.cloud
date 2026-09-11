from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from shared.security.require_admin import AdminPrincipal, require_admin

from dispatch.adapter.inbound.api.schemas.spam_schema import (
    SpamClassifyRequest,
    SpamClassifyResponse,
)
from dispatch.app.ports.input.spam_use_case import SpamClassifyUseCase
from dispatch.app.ports.output.spam_errors import SpamFilterError
from dispatch.dependencies.spam_provider import get_spam_classify_use_case

spam_router = APIRouter(prefix="/spam", tags=["dispatch-spam"])


# 2026-09-11 리뷰 H4: 익명이 임의 텍스트로 LLM(EXAONE/Ollama) 호출을 소모할
# 수 있던 표면 — 프론트 호출처 0건 실측, admin 전용으로 잠근다.
@spam_router.post("/classify", response_model=SpamClassifyResponse)
def classify_spam(
    req: SpamClassifyRequest,
    use_case: SpamClassifyUseCase = Depends(get_spam_classify_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> SpamClassifyResponse:
    try:
        dto = use_case.classify(subject=req.subject, body=req.body, sender=req.sender)
    except SpamFilterError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return SpamClassifyResponse(category=dto.category, is_spam=dto.is_spam, reason=dto.reason)
