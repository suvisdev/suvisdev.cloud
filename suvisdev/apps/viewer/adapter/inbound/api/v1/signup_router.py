from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from viewer.adapter.inbound.api.schemas.signup_schema import SignupSchema
from viewer.adapter.outbound.pg.signup_pg_repository import SignupRepositoryError
from viewer.app.ports.input.signup_use_case import SignupUseCase
from viewer.dependencies.signup_provider import get_signup_use_case

signup_router = APIRouter(prefix="/signup", tags=["signup"])
logger = logging.getLogger(__name__)


@signup_router.post("/signup", response_model=int)
async def signup(
    request: SignupSchema,
    signup: SignupUseCase = Depends(get_signup_use_case),
) -> int:
    logger.info("🤖 [SignupRouter] signup 진입 — %s", request.log_summary())
    try:
        result = await signup.signup(request)
    except SignupRepositoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    logger.info("🤖 [SignupRouter] signup 완료 — user_id=%s", result.user_id)
    return result.user_id
