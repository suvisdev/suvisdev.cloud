import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import UnidentifiedImageError

from ontology.app.dtos.face_dto import FacePredictResult, FaceTrainResult
from ontology.app.ports.input.face_use_case import FaceUseCase
from ontology.dependencies.face_provider import get_face_use_case

face_router = APIRouter(tags=["vision-face"])


@face_router.post("/face/train")
async def train_face_model(
    epochs: int = 10,
    batch: int = 8,
    imgsz: int = 224,
    face: FaceUseCase = Depends(get_face_use_case),
) -> FaceTrainResult:
    try:
        return await asyncio.to_thread(face.train, epochs, batch, imgsz)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@face_router.post("/face/predict")
async def predict_face(
    file: UploadFile = File(...),
    face: FaceUseCase = Depends(get_face_use_case),
) -> FacePredictResult:
    content = await file.read()
    try:
        return await asyncio.to_thread(face.predict, content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.") from e
