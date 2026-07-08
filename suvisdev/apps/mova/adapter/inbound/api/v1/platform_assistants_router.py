"""어시스턴트 라우터 — GET /mova/assistants"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.platform_assistants_schema import (
    AssistantListSchema,
    AssistantSchema,
)
from mova.app.ports.input.platform_assistants_use_case import AssistantsUseCase
from mova.dependencies.platform_assistants_provider import get_assistants_use_case

platform_assistants_router = APIRouter(prefix="/assistants", tags=["mova-assistants"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@platform_assistants_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="AI 컨시어지 (AI Concierge)")


@platform_assistants_router.get("", response_model=AssistantListSchema)
async def list_assistants(
    assistants: AssistantsUseCase = Depends(get_assistants_use_case),
) -> AssistantListSchema:
    """활성화된 어시스턴트 목록 조회."""
    dto = await assistants.list_assistants()
    return dto.to_schema()


@platform_assistants_router.get("/{slug}", response_model=AssistantSchema)
async def get_assistant(
    slug: str,
    assistants: AssistantsUseCase = Depends(get_assistants_use_case),
) -> AssistantSchema:
    """slug로 어시스턴트 단건 조회."""
    dto = await assistants.get_assistant(slug)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Assistant '{slug}' not found")
    return dto.to_schema()
