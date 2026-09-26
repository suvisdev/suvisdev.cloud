"""홈 포트폴리오 채팅 DTO — 공개 문서 근거 질의응답(2026-09-27)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ontology.adapter.inbound.api.schemas.portfolio_chat_schema import (
        PortfolioChatRequest,
        PortfolioChatResponseSchema,
    )


@dataclass(frozen=True)
class PortfolioChatTurn:
    role: str
    content: str


@dataclass(frozen=True)
class PortfolioChatCommand:
    message: str
    history: tuple[PortfolioChatTurn, ...] = ()

    @classmethod
    def from_schema(cls, schema: PortfolioChatRequest) -> PortfolioChatCommand:
        return cls(
            message=schema.message.strip(),
            history=tuple(
                PortfolioChatTurn(role=t.role, content=t.content) for t in schema.history
            ),
        )


@dataclass(frozen=True)
class PortfolioChatAnswerDto:
    reply: str
    sources: tuple[str, ...]

    def to_schema(self) -> PortfolioChatResponseSchema:
        from ontology.adapter.inbound.api.schemas.portfolio_chat_schema import (
            PortfolioChatResponseSchema,
        )

        return PortfolioChatResponseSchema(reply=self.reply, sources=list(self.sources))
