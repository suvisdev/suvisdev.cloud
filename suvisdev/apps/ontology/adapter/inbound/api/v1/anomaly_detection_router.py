import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import UnidentifiedImageError

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult
from ontology.app.ports.input.anomaly_detection_use_case import AnomalyDetectionUseCase
from ontology.dependencies.anomaly_detection_provider import get_anomaly_detection_use_case

anomaly_detection_router = APIRouter(tags=["vision-sentinel"])


@anomaly_detection_router.post("/sentinel/detect")
async def detect_anomaly(
    file: UploadFile = File(...),
    detector: AnomalyDetectionUseCase = Depends(get_anomaly_detection_use_case),
) -> AnomalyResult:
    content = await file.read()
    # 호출당 CLIP 로드(§6.7, 수십 초) — 이벤트 루프 블로킹 방지
    try:
        return await asyncio.to_thread(detector.detect, content)
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.") from e
