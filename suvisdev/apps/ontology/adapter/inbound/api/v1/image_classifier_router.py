import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import UnidentifiedImageError

from ontology.app.dtos.image_classifier_dto import Prediction
from ontology.app.ports.input.image_classifier_use_case import ImageClassifierUseCase
from ontology.dependencies.image_classifier_provider import get_image_classifier_use_case

image_classifier_router = APIRouter(tags=["vision-genre"])


@image_classifier_router.post("/genre/classify")
async def classify_poster(
    file: UploadFile = File(...),
    classifier: ImageClassifierUseCase = Depends(get_image_classifier_use_case),
) -> list[Prediction]:
    content = await file.read()
    try:
        return await asyncio.to_thread(classifier.classify, content)
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.") from e


@image_classifier_router.get("/genre/classes")
async def list_genre_classes(
    classifier: ImageClassifierUseCase = Depends(get_image_classifier_use_case),
) -> list[str]:
    return classifier.supported_classes()
