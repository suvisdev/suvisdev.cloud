"""susu(Flutter) 카메라 사진 → S3 저장 전용. Sentinel(ontology/vision) 이상탐지
파이프라인과는 완전히 분리 — 블러·포스터 게이트 없이 그대로 저장만 한다."""

from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.matrix.aws_tank_s3_manager import get_tank
from media.dependencies.require_auth import get_current_user
from media.schemas import PhotoUploadResponse
from shared.security.token_verifier import TokenPayload

media_router = APIRouter(prefix="/media", tags=["media"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 10 * 1024 * 1024  # 10MB


@media_router.post("/photos", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    user: TokenPayload = Depends(get_current_user),
) -> PhotoUploadResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(content) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 10MB).")

    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="JPG/PNG/WebP 이미지만 업로드할 수 있습니다.")

    key = f"media/{user.sub}/{datetime.now():%Y%m%d_%H%M%S}_{file.filename}"
    tank = get_tank()
    try:
        url = await asyncio.to_thread(
            tank.upload_bytes, key, content, content_type=content_type
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return PhotoUploadResponse(
        key=key, url=url, size_bytes=len(content), content_type=content_type
    )
