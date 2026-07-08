from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from vision.adapter.inbound.api.schemas.vision_schema import VisionIntroduceSchema
from vision.app.dtos.vision_dto import VisionIntroduceResponse, VisionUploadResponse
from vision.app.ports.input.vision_use_case import VisionUseCase
from vision.dependencies.vision_provider import get_vision_use_case

vision_introduce_router = APIRouter(tags=["vision"])


@vision_introduce_router.get("/myself")
async def introduce_myself(
    vision: VisionUseCase = Depends(get_vision_use_case),
) -> VisionIntroduceResponse:
    return await vision.introduce_myself(
        VisionIntroduceSchema(id=1, name="비전"),
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
