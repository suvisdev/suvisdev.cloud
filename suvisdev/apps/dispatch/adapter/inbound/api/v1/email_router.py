from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dispatch.adapter.inbound.api.schemas.email_schema import (
    EmailIntroduceSchema,
    EmailRequest,
    EmailResponseSchema,
)
from dispatch.app.dtos.email_dto import EmailIntroduceResponse
from dispatch.app.ports.input.email_use_case import EmailUseCase
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.dependencies.email_provider import get_email_use_case

email_router = APIRouter(prefix="/email", tags=["dispatch-email"])


@email_router.get("/myself")
async def introduce_myself(
    use_case: EmailUseCase = Depends(get_email_use_case),
) -> EmailIntroduceResponse:
    return await use_case.introduce_myself(EmailIntroduceSchema(id=1, name="AI 메일 발송"))


@email_router.post("", response_model=EmailResponseSchema)
def send_email(
    req: EmailRequest,
    use_case: EmailUseCase = Depends(get_email_use_case),
) -> EmailResponseSchema:
    try:
        dto = use_case.send(to=str(req.to), prompt=req.prompt, subject=req.subject)
    except DispatchError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return EmailResponseSchema(success=True, to=dto.to, subject=dto.subject)
