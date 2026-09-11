import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import UnidentifiedImageError
from shared.security.require_admin import AdminPrincipal, require_admin

from ontology.app.dtos.image_classifier_dto import Prediction
from ontology.app.ports.input.image_classifier_use_case import ImageClassifierUseCase
from ontology.dependencies.image_classifier_provider import get_image_classifier_use_case

image_classifier_router = APIRouter(tags=["vision-genre"])

# vision_router `/upload`와 동일 근거(2026-09-11 리뷰 H4): 무인증 + 무제한
# 업로드 + 호출당 모델 로드는 DoS 표면. 프론트 호출처가 없어 admin 전용.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@image_classifier_router.post("/genre/classify")
async def classify_poster(
    file: UploadFile = File(...),
    classifier: ImageClassifierUseCase = Depends(get_image_classifier_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> list[Prediction]:
    content = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 10MB).")
    try:
        return await asyncio.to_thread(classifier.classify, content)
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.") from e


@image_classifier_router.get("/genre/classes")
async def list_genre_classes(
    classifier: ImageClassifierUseCase = Depends(get_image_classifier_use_case),
) -> list[str]:
    return classifier.supported_classes()
