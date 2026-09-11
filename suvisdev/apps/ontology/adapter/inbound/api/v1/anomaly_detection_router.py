import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import UnidentifiedImageError
from shared.security.require_admin import AdminPrincipal, require_admin

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult
from ontology.app.ports.input.anomaly_detection_use_case import AnomalyDetectionUseCase
from ontology.dependencies.anomaly_detection_provider import get_anomaly_detection_use_case

anomaly_detection_router = APIRouter(tags=["vision-sentinel"])

# vision_router `/upload`와 동일 근거(2026-09-11 리뷰 H4): 무인증 + 무제한
# 업로드 + 호출당 모델 로드는 DoS 표면. 프론트 호출처가 없어 admin 전용.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@anomaly_detection_router.post("/sentinel/detect")
async def detect_anomaly(
    file: UploadFile = File(...),
    detector: AnomalyDetectionUseCase = Depends(get_anomaly_detection_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> AnomalyResult:
    content = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 10MB).")
    # 호출당 CLIP 로드(§6.7, 수십 초) — 이벤트 루프 블로킹 방지
    try:
        return await asyncio.to_thread(detector.detect, content)
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.") from e
