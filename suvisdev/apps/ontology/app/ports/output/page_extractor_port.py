from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.custom_scrape_dto import ExtractedPage


class PageExtractorPort(ABC):
    @abstractmethod
    async def extract(self, html: str, instruction: str) -> ExtractedPage:
        """raw HTML에서 instruction이 요구하는 내용만 뽑아낸다."""
