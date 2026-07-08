from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from spam_filter.adapter.inbound.api.schemas.spam_schema import SpamClassifyRequest, SpamClassifyResponse
from spam_filter.app.ports.input.spam_use_case import SpamClassifyUseCase
from spam_filter.app.ports.output.spam_errors import SpamFilterError
from spam_filter.dependencies.spam_provider import get_spam_classify_use_case

spam_router = APIRouter(prefix="/spam", tags=["spam-filter"])


@spam_router.post("/classify", response_model=SpamClassifyResponse)
def classify_spam(
    req: SpamClassifyRequest,
    use_case: SpamClassifyUseCase = Depends(get_spam_classify_use_case),
) -> SpamClassifyResponse:
    try:
        dto = use_case.classify(subject=req.subject, body=req.body, sender=req.sender)
    except SpamFilterError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return SpamClassifyResponse(category=dto.category, is_spam=dto.is_spam, reason=dto.reason)
