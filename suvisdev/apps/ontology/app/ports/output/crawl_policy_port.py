from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.crawl_schedule_dto import CrawlPolicy


class CrawlPolicyPort(ABC):
    @abstractmethod
    def get_policies(self) -> list[CrawlPolicy]:
        """crawl_config.yaml 등에 등록된 모든 재수집 정책을 가져온다."""
