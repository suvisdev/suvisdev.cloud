from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.app.dtos.pdf_loader_dto import PdfLoaderRecord, PdfLoaderResponse


class PdfLoaderPort(ABC):
    """PDF 요약 결과 저장 아웃바운드 포트 (ABC)."""

    @abstractmethod
    async def save(self, record: PdfLoaderRecord) -> PdfLoaderResponse:
        pass
