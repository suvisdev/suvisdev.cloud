"""vision 어드민 오버라이드 HTTP 스키마."""

from __future__ import annotations

from pydantic import BaseModel


class VisionPosterFlagUpdateSchema(BaseModel):
    is_poster_warning: bool


class VisionPosterFlagSchema(BaseModel):
    upload_id: int
    is_poster_warning: bool
    updated: bool
