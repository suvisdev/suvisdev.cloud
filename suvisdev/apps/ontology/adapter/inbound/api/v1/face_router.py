import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import UnidentifiedImageError
from shared.security.require_admin import AdminPrincipal, require_admin
from shared.security.require_user import UserPrincipal, require_user

from ontology.app.dtos.face_dto import FacePredictResult, FaceTrainResult
from ontology.app.ports.input.face_use_case import FaceUseCase
from ontology.dependencies.face_provider import get_face_use_case

face_router = APIRouter(tags=["vision-face"])

# 2026-09-11 리뷰 H4: train은 익명이 GPU를 무기한 점유할 수 있어(epochs 상한
# 부재) admin 전용 + 파라미터 상한. predict는 데모 페이지(AdminAuthGate 뒤
# object-detection)가 호출하므로 vision `/upload`와 같은 require_user + 10MB.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@face_router.post("/face/train")
async def train_face_model(
    epochs: int = Query(10, ge=1, le=100),
    batch: int = Query(8, ge=1, le=64),
    imgsz: int = Query(224, ge=64, le=1024),
    face: FaceUseCase = Depends(get_face_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> FaceTrainResult:
    try:
        return await asyncio.to_thread(face.train, epochs, batch, imgsz)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@face_router.post("/face/predict")
async def predict_face(
    file: UploadFile = File(...),
    face: FaceUseCase = Depends(get_face_use_case),
    _: UserPrincipal = Depends(require_user),
) -> FacePredictResult:
    content = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 10MB).")
    try:
        return await asyncio.to_thread(face.predict, content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.") from e
