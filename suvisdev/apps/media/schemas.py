from __future__ import annotations

from pydantic import BaseModel


class PhotoUploadResponse(BaseModel):
    key: str
    url: str
    size_bytes: int
    content_type: str
