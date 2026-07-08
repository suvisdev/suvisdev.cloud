from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReceiveRequestSchema(BaseModel):
    sender: str = ""
    subject: str = ""
    body: str = ""


class ReceiveItemSchema(BaseModel):
    id: int
    sender: str
    subject: str
    body: str
    received_at: datetime
