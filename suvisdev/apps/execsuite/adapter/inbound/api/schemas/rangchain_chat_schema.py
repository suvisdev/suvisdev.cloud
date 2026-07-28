from __future__ import annotations

from pydantic import BaseModel


class RangchainChatMessageSchema(BaseModel):
    role: str
    content: str


class RangchainChatRequestSchema(BaseModel):
    messages: list[RangchainChatMessageSchema]
    model: str | None = None
    systemInstruction: str | None = None


class RangchainChatResponseSchema(BaseModel):
    reply: str
