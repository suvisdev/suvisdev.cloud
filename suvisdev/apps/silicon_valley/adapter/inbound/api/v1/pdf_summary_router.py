from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from silicon_valley.app.dtos.pdf_summary_dto import PdfSummaryResponse
from silicon_valley.app.ports.input.pdf_summary_use_case import PdfSummaryUseCase
from silicon_valley.dependencies.pdf_summary_provider import get_pdf_summary_use_case

pdf_summary_router = APIRouter(prefix="/pdf", tags=["pdf"])


@pdf_summary_router.post("/summarize")
async def summarize_pdf(
    file: UploadFile = File(...),
    pdf_summary: PdfSummaryUseCase = Depends(get_pdf_summary_use_case),
) -> PdfSummaryResponse:
    content = await file.read()
    try:
        return await pdf_summary.summarize_pdf(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
