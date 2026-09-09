from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from shared.security.require_admin import AdminPrincipal, require_admin
from shared.security.require_user import UserPrincipal, require_user

from ontology.adapter.inbound.api.schemas.vision_schema import (
    VisionPosterFlagSchema,
    VisionPosterFlagUpdateSchema,
)
from ontology.app.dtos.vision_dto import (
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionUploadResponse,
)
from ontology.app.ports.input.vision_use_case import VisionUseCase
from ontology.dependencies.vision_provider import get_vision_use_case

vision_introduce_router = APIRouter(tags=["vision"])

# 무인증 + 무제한 크기 + GPU(CLIP) 추론은 DoS 표면이라 로그인·크기·타입으로 막는다.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB (media 업로드와 동일)
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@vision_introduce_router.get("/myself")
async def introduce_myself(
    vision: VisionUseCase = Depends(get_vision_use_case),
) -> VisionIntroduceResponse:
    return await vision.introduce_myself(
        VisionIntroduceQuery(id=1, name="비전"),
    )


@vision_introduce_router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _: UserPrincipal = Depends(require_user),
    vision: VisionUseCase = Depends(get_vision_use_case),
) -> VisionUploadResponse:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="이미지 파일(jpeg/png/webp/gif)만 가능해요.")
    # Content-Length가 있으면 읽기 전에 거른다(메모리에 통째로 올리기 전 차단).
    if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="이미지는 10MB 이하만 업로드할 수 있어요.")
    content = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="이미지는 10MB 이하만 업로드할 수 있어요.")
    try:
        return await vision.upload_image(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@vision_introduce_router.patch("/{upload_id}/poster-flag", response_model=VisionPosterFlagSchema)
async def override_poster_flag(
    upload_id: int,
    body: VisionPosterFlagUpdateSchema,
    _: AdminPrincipal = Depends(require_admin),
    vision: VisionUseCase = Depends(get_vision_use_case),
) -> VisionPosterFlagSchema:
    """Sentinel 소프트 플래그(is_poster_warning) 어드민 수동 재판정."""
    dto = await vision.override_poster_flag(upload_id, body.is_poster_warning)
    if not dto.updated:
        raise HTTPException(status_code=404, detail=f"vision_uploads id={upload_id} 없음")
    return VisionPosterFlagSchema(
        upload_id=dto.upload_id, is_poster_warning=dto.is_poster_warning, updated=dto.updated
    )
