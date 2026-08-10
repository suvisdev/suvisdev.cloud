from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from shared.security.require_user import UserPrincipal, require_user
from viewer.app.ports.input.profile_use_case import ProfileUseCase
from viewer.dependencies.profile_provider import get_profile_use_case

avatar_router = APIRouter(prefix="/avatar", tags=["avatar"])

# 확장자는 우리가 S3 key를 조립할 때 쓰는 값이라 MIME과 짝지어 고정한다 —
# 파일명에 들어온 확장자를 그대로 믿지 않는다(경로 조작·이중 확장자 방지).
_ALLOWED_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_MAX_BYTES = 5 * 1024 * 1024
_CHUNK_BYTES = 64 * 1024


class AvatarUploadResponse(BaseModel):
    avatar_key: str
    avatar_url: str | None


async def _read_limited(file: UploadFile) -> bytes:
    """상한을 넘는 순간 읽기를 멈춘다.

    전부 읽고 `len()`을 재는 방식(media 앱 선례)은 상한 초과 요청도 일단 통째로
    메모리에 올린다. `UploadFile.spool_max_size`는 메모리→디스크 스풀 전환
    임계값이지 업로드 상한이 아니라 검증에 쓸 수 없다.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK_BYTES):
        total += len(chunk)
        if total > _MAX_BYTES:
            raise HTTPException(status_code=413, detail="이미지는 5MB까지 올릴 수 있습니다.")
        chunks.append(chunk)
    return b"".join(chunks)


@avatar_router.post("/upload", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    principal: UserPrincipal = Depends(require_user),
    profile: ProfileUseCase = Depends(get_profile_use_case),
) -> AvatarUploadResponse:
    # 대상 사용자는 토큰에서만 온다 — 경로·바디로 user_id를 받지 않으므로
    # 남의 아바타를 바꿀 경로 자체가 없다.
    ext = _ALLOWED_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status_code=415, detail="JPG/PNG/WebP 이미지만 올릴 수 있습니다.")

    data = await _read_limited(file)
    if not data:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    try:
        result = await profile.upload_avatar(
            principal.user_id, data, content_type=file.content_type or "", ext=ext
        )
    except RuntimeError as e:  # Tank가 S3 실패를 RuntimeError로 감싼다
        raise HTTPException(status_code=502, detail="이미지 저장에 실패했습니다.") from e

    if result is None:
        raise HTTPException(status_code=404, detail="회원 정보를 찾을 수 없습니다.")
    return AvatarUploadResponse(avatar_key=result.avatar_key or "", avatar_url=result.avatar_url)
