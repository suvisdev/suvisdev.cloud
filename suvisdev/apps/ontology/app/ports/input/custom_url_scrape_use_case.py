from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ontology.app.dtos.scrape_dto import DatasetMeta


class CustomUrlScrapeUseCase(ABC):
    @abstractmethod
    async def run(
        self, *, url: str, instruction: str, out_path: Path, append: bool = False
    ) -> DatasetMeta:
        """url 1건을 robots.txt 확인 후 가져와 instruction대로 추출하고 저장한다."""
