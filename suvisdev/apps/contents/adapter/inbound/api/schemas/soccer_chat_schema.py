from __future__ import annotations

from pydantic import BaseModel


class SoccerChatMessageSchema(BaseModel):
    role: str
    content: str


class SoccerChatRequestSchema(BaseModel):
    messages: list[SoccerChatMessageSchema]
    model: str | None = None
    systemInstruction: str | None = None


class SoccerChatResponseSchema(BaseModel):
    reply: str
