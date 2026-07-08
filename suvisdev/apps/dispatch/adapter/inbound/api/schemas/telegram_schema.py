from __future__ import annotations

from pydantic import BaseModel


class TelegramRequest(BaseModel):
    message: str
    chat_id: str | None = None


class TelegramResponseSchema(BaseModel):
    success: bool


class TelegramIntroduceSchema(BaseModel):
    id: int
    name: str
