from __future__ import annotations

from abc import ABC, abstractmethod


class PdfSummarizerPort(ABC):
    """추출된 텍스트 → 요약 아웃바운드 포트 (ABC)."""

    @abstractmethod
    async def summarize(self, text: str) -> str:
        pass
