from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ontology.app.dtos.scrape_dto import DatasetMeta, ScrapeTarget


class ScrapeDatasetUseCase(ABC):
    @abstractmethod
    def run(self, target: ScrapeTarget, *, limit: int, out_path: Path) -> DatasetMeta:
        """target 사이트에서 키워드 관련 레코드를 limit건까지 수집해 JSONL로 저장한다.

        dedup 여부·rate 간격은 여기서 받지 않는다 — CLI가 DI 시점에 그에 맞는
        VisitedStorePort/RateLimiterPort 구현체를 골라 SiteScraperPort에 주입해둔다.
        """
