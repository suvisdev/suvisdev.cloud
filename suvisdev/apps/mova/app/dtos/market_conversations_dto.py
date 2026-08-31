"""대화 스레드 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mova.adapter.inbound.api.schemas.market_conversations_schema import (
        ConversationDetailSchema,
        ConversationMessageSchema,
        ConversationSummarySchema,
    )


@dataclass(frozen=True)
class ConversationMessageDto:
    id: int
    role: str  # "user" | "assistant"
    content: str
    meta: dict[str, Any]
    created_at: datetime

    def to_schema(self) -> ConversationMessageSchema:
        from mova.adapter.inbound.api.schemas.market_conversations_schema import (
            ConversationMessageSchema,
        )

        return ConversationMessageSchema(
            id=self.id,
            role=self.role,  # type: ignore[arg-type]
            content=self.content,
            meta=self.meta,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class ConversationSummaryDto:
    id: int
    title: str
    updated_at: datetime
    message_count: int

    def to_schema(self) -> ConversationSummarySchema:
        from mova.adapter.inbound.api.schemas.market_conversations_schema import (
            ConversationSummarySchema,
        )

        return ConversationSummarySchema(
            id=self.id,
            title=self.title,
            updated_at=self.updated_at,
            message_count=self.message_count,
        )


@dataclass(frozen=True)
class ConversationDetailDto:
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageDto] = field(default_factory=list)

    def to_schema(self) -> ConversationDetailSchema:
        from mova.adapter.inbound.api.schemas.market_conversations_schema import (
            ConversationDetailSchema,
        )

        return ConversationDetailSchema(
            id=self.id,
            title=self.title,
            created_at=self.created_at,
            updated_at=self.updated_at,
            messages=[m.to_schema() for m in self.messages],
        )
