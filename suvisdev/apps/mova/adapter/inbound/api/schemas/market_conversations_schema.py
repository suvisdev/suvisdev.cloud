"""대화 스레드 API 스키마 — /mova/conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationSummarySchema(BaseModel):
    """사이드바 목록 항목."""

    id: int
    title: str
    updated_at: datetime
    message_count: int = 0


class ConversationMessageSchema(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationDetailSchema(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageSchema] = Field(default_factory=list)
