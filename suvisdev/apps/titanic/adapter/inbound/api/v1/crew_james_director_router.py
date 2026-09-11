import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from shared.security.require_admin import AdminPrincipal, require_admin

from titanic.adapter.inbound.api.schemas.crew_james_director_schema import JamesIntroduceSchema
from titanic.app.dtos.crew_james_director_dto import JamesIntroduceResponse, JamesResponse
from titanic.app.ports.input.crew_james_director_use_case import JamesUseCase
from titanic.dependencies.crew_james_director_provider import get_james_director_use_case

james_director_router = APIRouter(prefix="/james", tags=["james"])
logger = logging.getLogger(__name__)


@james_director_router.get("/myself")
async def introduce_myself(
    james: JamesUseCase = Depends(get_james_director_use_case),
) -> JamesIntroduceResponse:
    return await james.introduce_myself(
        JamesIntroduceSchema(
            id=12,
            name="제임스 카메론 (James Cameron)",
        )
    )


# 2026-09-11 리뷰 H4: 무인증 DB 쓰기 + 무제한 read였다 — 호출처는
# AdminAuthGate 뒤 데이터 수집 페이지뿐이라 admin 전용 + 10MB 상한.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@james_director_router.post("/upload")
async def receive_uploaded_records(
    file: UploadFile = File(...),
    james: JamesUseCase = Depends(get_james_director_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> JamesResponse:
    raw = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 10MB).")
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        return await james.receive_uploaded_records(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
