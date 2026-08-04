"""susu(Flutter) 카메라 사진 → S3 저장 전용. Sentinel(ontology/vision) 이상탐지
파이프라인과는 완전히 분리 — 블러·포스터 게이트 없이 그대로 저장만 한다."""

from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.matrix.aws_tank_s3_manager import get_tank
from media.dependencies.require_auth import get_current_user
from media.ocr import extract_text
from media.schemas import OcrPhotoItem, PhotoUploadResponse
from shared.security.require_admin import AdminPrincipal, require_admin
from shared.security.token_verifier import TokenPayload

media_router = APIRouter(prefix="/media", tags=["media"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 10 * 1024 * 1024  # 10MB
_MAX_OCR_ITEMS = 12  # 사진 1장당 Gemini 호출 1회 — 레슨 데모 페이지 응답 시간 보호


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


@media_router.get("/photos/ocr", response_model=list[OcrPhotoItem])
async def list_photos_with_ocr(
    admin: AdminPrincipal = Depends(require_admin),
) -> list[OcrPhotoItem]:
    """suvis 웹 레슨 페이지 전용 — 관리자 본인이 susu로 올린 사진만 OCR해서 보여준다.
    require_admin(HS256, viewer 로그인 체계)을 쓴다 — susu 업로드가 쓰는
    get_current_user(RS256, aud=suvis-susu)와는 다른 토큰 체계지만, 두 체계 모두
    같은 users 테이블 user_id를 sub/user_id로 쓰므로 prefix가 그대로 맞는다."""
    tank = get_tank()
    prefix = f"media/{admin.user_id}/"
    try:
        keys = await asyncio.to_thread(tank.list_objects, prefix)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    keys.sort(reverse=True)  # 파일명에 타임스탬프가 있어 최신순 정렬됨
    items: list[OcrPhotoItem] = []
    for key in keys[:_MAX_OCR_ITEMS]:
        try:
            image_bytes = await asyncio.to_thread(tank.download_bytes, key)
        except RuntimeError:
            continue  # 개별 객체 조회 실패는 건너뛴다(전체 목록을 막지 않음)

        content_type = mimetypes.guess_type(key)[0] or "image/jpeg"
        try:
            text = await asyncio.to_thread(extract_text, image_bytes, content_type)
        except RuntimeError:
            text = "(텍스트 추출 실패)"  # OCR 실패해도 사진 자체는 보여준다

        url = tank.generate_presigned_url(key)
        items.append(OcrPhotoItem(image_url=url, extracted_text=text))

    return items
