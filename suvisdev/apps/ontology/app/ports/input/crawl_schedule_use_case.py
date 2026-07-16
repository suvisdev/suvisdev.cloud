from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ontology.app.dtos.scrape_dto import DatasetMeta


class CrawlScheduleUseCase(ABC):
    @abstractmethod
    def run_due_batches(self, *, now: datetime | None = None) -> list[DatasetMeta]:
        """CrawlPolicy 중 interval이 지난 사이트만 골라 증분 수집하고 crawl.completed를 발행한다."""

    @abstractmethod
    def run_once(self, *, site_id: str, keywords: tuple[str, ...], limit: int) -> DatasetMeta:
        """due-check 없이 즉시 1회 수집한다 (어드민 화면 등 온디맨드 트리거용)."""
