from __future__ import annotations

from pydantic import BaseModel


class PhotoUploadResponse(BaseModel):
    key: str
    url: str
    size_bytes: int
    content_type: str


class OcrPhotoItem(BaseModel):
    image_url: str
    extracted_text: str
    user_id: str
