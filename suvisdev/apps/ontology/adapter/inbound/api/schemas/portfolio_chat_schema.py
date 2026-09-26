"""홈 포트폴리오 채팅 요청/응답 스키마(2026-09-27)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PortfolioChatTurnSchema(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class PortfolioChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[PortfolioChatTurnSchema] = Field(default_factory=list, max_length=10)


class PortfolioChatResponseSchema(BaseModel):
    reply: str
    sources: list[str] = []
