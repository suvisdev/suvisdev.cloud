from __future__ import annotations

from abc import ABC, abstractmethod

from silicon_valley.app.dtos.pdf_summary_dto import PdfSummaryResponse


class PdfSummaryUseCase(ABC):
    """PDF 업로드 → 추출 → 요약 입력 포트 (ABC)."""

    @abstractmethod
    async def summarize_pdf(self, filename: str, content: bytes) -> PdfSummaryResponse:
        pass
