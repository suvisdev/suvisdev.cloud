from __future__ import annotations

from silicon_valley.app.dtos.pdf_loader_dto import PdfLoaderRecord, PdfLoaderResponse
from silicon_valley.app.ports.input.pdf_loader_use_case import PdfLoaderUseCase
from silicon_valley.app.ports.output.pdf_loader_extractor_port import PdfExtractorPort
from silicon_valley.app.ports.output.pdf_loader_repository_port import PdfLoaderPort
from silicon_valley.app.ports.output.pdf_loader_summarizer_port import PdfSummarizerPort

_ALLOWED_EXTENSION = ".pdf"


class PdfLoaderInteractor(PdfLoaderUseCase):
    """pdf_loader_router → 입력 포트 → 추출·요약 → 출력 포트(repository)."""

    def __init__(
        self,
        extractor: PdfExtractorPort,
        summarizer: PdfSummarizerPort,
        repository: PdfLoaderPort,
    ) -> None:
        self._extractor = extractor
        self._summarizer = summarizer
        self._repository = repository

    async def summarize_pdf(self, filename: str, content: bytes) -> PdfLoaderResponse:
        if not filename.lower().endswith(_ALLOWED_EXTENSION):
            raise ValueError("PDF 파일만 업로드할 수 있습니다.")
        if not content:
            raise ValueError("빈 파일입니다.")

        document = await self._extractor.extract_text(filename, content)
        if not document.text.strip():
            raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

        summary = await self._summarizer.summarize(document.text)

        return await self._repository.save(
            PdfLoaderRecord(
                filename=filename,
                extracted_text=document.text,
                summary=summary,
            ),
        )
