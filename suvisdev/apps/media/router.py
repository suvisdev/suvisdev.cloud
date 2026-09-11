"""susu(Flutter) 카메라 사진 → S3 저장 전용. Sentinel(ontology/vision) 이상탐지
파이프라인과는 완전히 분리 — 블러·포스터 게이트 없이 그대로 저장만 한다."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from shared.security.require_admin import AdminPrincipal, require_admin
from shared.security.token_verifier import TokenPayload

from core.matrix.aws_tank_s3_manager import get_tank
from media.dependencies.require_auth import get_current_user
from media.ocr import extract_text
from media.schemas import OcrPhotoItem, PhotoUploadResponse

logger = logging.getLogger(__name__)

media_router = APIRouter(prefix="/media", tags=["media"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 10 * 1024 * 1024  # 10MB
_MAX_OCR_ITEMS = 12  # 사진 1장당 Gemini 호출 1회 — 레슨 데모 페이지 응답 시간 보호


@media_router.post("/photos", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    user: TokenPayload = Depends(get_current_user),
) -> PhotoUploadResponse:
    # 상한+1바이트까지만 읽는다 — 전체를 메모리에 올린 뒤 거부하면 10MB 검사가
    # 무의미해진다(초과 업로드도 서버 메모리를 다 쓰고 나서야 400).
    content = await file.read(_MAX_BYTES + 1)
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
        url = await asyncio.to_thread(tank.upload_bytes, key, content, content_type=content_type)
    except RuntimeError as e:
        logger.error("[media] S3 업로드 실패 key=%s err=%s", key, e)
        raise HTTPException(status_code=502, detail="사진 저장에 실패했습니다.") from e

    return PhotoUploadResponse(key=key, url=url, size_bytes=len(content), content_type=content_type)


@media_router.get("/photos/ocr", response_model=list[OcrPhotoItem])
async def list_photos_with_ocr(
    admin: AdminPrincipal = Depends(require_admin),
) -> list[OcrPhotoItem]:
    """suvis 웹 레슨 페이지 전용 — require_admin(HS256, viewer 로그인 체계)이면
    susu로 올라온 전체 사용자 사진을 OCR해서 보여준다. susu 업로드가 쓰는
    get_current_user(RS256, aud=suvis-susu)와는 다른 토큰 체계인데, susu(카카오)와
    웹 관리자(구글) 로그인이 users 테이블에서 서로 다른 계정으로 남는 경우가 있어
    관리자 본인 user_id로 좁히면 다른 사용자가 올린 사진이 안 보이는 문제가 있었다
    — admin 권한 자체가 이미 전체 열람을 전제하므로 prefix를 media/ 전체로 연다."""
    tank = get_tank()
    try:
        keys = await asyncio.to_thread(tank.list_objects, "media/")
    except RuntimeError as e:
        logger.error("[media] S3 목록 조회 실패 err=%s", e)
        raise HTTPException(status_code=502, detail="사진 목록 조회에 실패했습니다.") from e

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
        # key = "media/{user_id}/{filename}" — 다른 형태(버킷 루트 등)면 알 수 없음 처리
        parts = key.split("/")
        user_id = parts[1] if len(parts) >= 3 and parts[0] == "media" else "?"
        items.append(OcrPhotoItem(image_url=url, extracted_text=text, user_id=user_id))

    return items
