from __future__ import annotations

from silicon_valley.app.dtos.pdf_summary_dto import PdfSummaryRecord, PdfSummaryResponse
from silicon_valley.app.ports.input.pdf_summary_use_case import PdfSummaryUseCase
from silicon_valley.app.ports.output.pdf_summary_extractor_port import PdfExtractorPort
from silicon_valley.app.ports.output.pdf_summary_repository_port import PdfSummaryPort
from silicon_valley.app.ports.output.pdf_summary_summarizer_port import PdfSummarizerPort

_ALLOWED_EXTENSION = ".pdf"


class PdfSummaryInteractor(PdfSummaryUseCase):
    """pdf_summary_router → 입력 포트 → 추출·요약 → 출력 포트(repository)."""

    def __init__(
        self,
        extractor: PdfExtractorPort,
        summarizer: PdfSummarizerPort,
        repository: PdfSummaryPort,
    ) -> None:
        self._extractor = extractor
        self._summarizer = summarizer
        self._repository = repository

    async def summarize_pdf(self, filename: str, content: bytes) -> PdfSummaryResponse:
        if not filename.lower().endswith(_ALLOWED_EXTENSION):
            raise ValueError("PDF 파일만 업로드할 수 있습니다.")
        if not content:
            raise ValueError("빈 파일입니다.")

        document = await self._extractor.extract_text(filename, content)
        if not document.text.strip():
            raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

        summary = await self._summarizer.summarize(document.text)

        return await self._repository.save(
            PdfSummaryRecord(
                filename=filename,
                extracted_text=document.text,
                summary=summary,
            ),
        )
