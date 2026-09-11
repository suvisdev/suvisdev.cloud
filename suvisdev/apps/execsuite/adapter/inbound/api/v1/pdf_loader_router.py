from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from shared.security.require_admin import AdminPrincipal, require_admin

from execsuite.app.dtos.pdf_loader_dto import PdfLoaderResponse
from execsuite.app.ports.input.pdf_loader_use_case import PdfLoaderUseCase
from execsuite.dependencies.pdf_loader_provider import get_pdf_loader_use_case

pdf_loader_router = APIRouter(prefix="/pdf", tags=["pdf"])

# 2026-09-11 리뷰 H4: 익명 무제한 PDF → 추출 → LLM 요약 → 전문 DB 저장
# 경로였다 — 프론트 호출처가 없어 admin 전용 + 10MB 상한.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@pdf_loader_router.post("/summarize")
async def summarize_pdf(
    file: UploadFile = File(...),
    pdf_loader: PdfLoaderUseCase = Depends(get_pdf_loader_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> PdfLoaderResponse:
    content = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 10MB).")
    try:
        return await pdf_loader.summarize_pdf(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
