from __future__ import annotations

from pydantic import BaseModel


class LangchainChatMessageSchema(BaseModel):
    role: str
    content: str


class LangchainChatRequestSchema(BaseModel):
    messages: list[LangchainChatMessageSchema]
    model: str | None = None
    systemInstruction: str | None = None


class LangchainChatResponseSchema(BaseModel):
    reply: str
