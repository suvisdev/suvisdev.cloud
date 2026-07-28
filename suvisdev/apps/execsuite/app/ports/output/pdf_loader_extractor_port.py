from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.app.dtos.pdf_loader_dto import PdfExtractedDocument


class PdfExtractorPort(ABC):
    """PDF 바이트 → 텍스트 추출 아웃바운드 포트 (ABC)."""

    @abstractmethod
    async def extract_text(self, filename: str, content: bytes) -> PdfExtractedDocument:
        pass
