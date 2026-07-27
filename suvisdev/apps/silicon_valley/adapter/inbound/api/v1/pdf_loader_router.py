from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from silicon_valley.app.dtos.pdf_loader_dto import PdfLoaderResponse
from silicon_valley.app.ports.input.pdf_loader_use_case import PdfLoaderUseCase
from silicon_valley.dependencies.pdf_loader_provider import get_pdf_loader_use_case

pdf_loader_router = APIRouter(prefix="/pdf", tags=["pdf"])


@pdf_loader_router.post("/summarize")
async def summarize_pdf(
    file: UploadFile = File(...),
    pdf_loader: PdfLoaderUseCase = Depends(get_pdf_loader_use_case),
) -> PdfLoaderResponse:
    content = await file.read()
    try:
        return await pdf_loader.summarize_pdf(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
