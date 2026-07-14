from __future__ import annotations

from pydantic import BaseModel


class SpamClassifyRequest(BaseModel):
    subject: str
    body: str
    sender: str | None = None


class SpamClassifyResponse(BaseModel):
    category: str
    is_spam: bool
    reason: str
