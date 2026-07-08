"""picks HTTP 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PickFeedbackUpdateSchema(BaseModel):
    feedback: Literal["like", "dislike"] | None = None


class PickFeedbackSchema(BaseModel):
    pick_id: int
    feedback: str | None
    updated: bool
