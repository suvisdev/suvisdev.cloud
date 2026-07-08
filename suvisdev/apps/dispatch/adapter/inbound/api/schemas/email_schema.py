from __future__ import annotations

from pydantic import BaseModel


class EmailRequest(BaseModel):
    to: str
    prompt: str
    subject: str | None = None


class EmailResponseSchema(BaseModel):
    success: bool
    to: str
    subject: str


class EmailIntroduceSchema(BaseModel):
    id: int
    name: str
