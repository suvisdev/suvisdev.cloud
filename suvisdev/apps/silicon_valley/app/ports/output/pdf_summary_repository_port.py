from __future__ import annotations

from abc import ABC, abstractmethod

from silicon_valley.app.dtos.pdf_summary_dto import PdfSummaryRecord, PdfSummaryResponse


class PdfSummaryPort(ABC):
    """PDF 요약 결과 저장 아웃바운드 포트 (ABC)."""

    @abstractmethod
    async def save(self, record: PdfSummaryRecord) -> PdfSummaryResponse:
        pass
