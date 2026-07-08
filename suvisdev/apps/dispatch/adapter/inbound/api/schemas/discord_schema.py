from __future__ import annotations

from pydantic import BaseModel


class DiscordRequest(BaseModel):
    message: str
    username: str | None = None


class DiscordResponseSchema(BaseModel):
    success: bool


class DiscordIntroduceSchema(BaseModel):
    id: int
    name: str
