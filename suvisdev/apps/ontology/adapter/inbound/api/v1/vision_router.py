from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from shared.security.require_admin import AdminPrincipal, require_admin

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
    vision: VisionUseCase = Depends(get_vision_use_case),
) -> VisionUploadResponse:
    content = await file.read()
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
