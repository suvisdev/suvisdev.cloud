"""어시스턴트 HTTP 스키마."""

from __future__ import annotations

from pydantic import BaseModel


class AssistantSchema(BaseModel):
    id: int
    slug: str
    display_name: str
    avatar_url: str
    system_prompt: str
    default_model: str
    is_active: bool


class AssistantListSchema(BaseModel):
    items: list[AssistantSchema]
