from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar

from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.page_fetcher_port import PageFetcherPort
from ontology.app.ports.output.rate_limiter_port import RateLimiterPort
from ontology.app.ports.output.visited_store_port import VisitedStorePort


class SiteScraperPort(ABC):
    """사이트 1곳의 검색+추출을 한 번에 담당한다. SITE_REGISTRY에 site_id로 등록된다.

    생성자를 여기서 고정해둔 이유: harvester_provider가 SITE_REGISTRY에서 꺼낸 클래스를
    fetcher/rate_limiter/visited_store 세 개로 균일하게 조립하기 때문이다 — 사이트
    어댑터가 이 셋 외의 추가 설정이 필요 없다면 __init__을 따로 안 써도 된다.
    """

    site_id: ClassVar[str]
    fetcher_kind: ClassVar[str] = "httpx"  # "httpx" | "playwright" — sites 커맨드 표시용
    user_agent: ClassVar[str | None] = None  # 지정 시 harvester_provider가 이 UA로 fetcher를 만든다

    def __init__(
        self,
        *,
        fetcher: PageFetcherPort,
        rate_limiter: RateLimiterPort,
        visited_store: VisitedStorePort,
    ) -> None:
        self._fetcher = fetcher
        self._rate_limiter = rate_limiter
        self._visited_store = visited_store

    @abstractmethod
    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        """키워드로 검색해 결과를 순회하며 레코드를 yield한다 (limit 도달 시 조기 종료).

        구현체 내부에서 self._fetcher·self._rate_limiter·self._visited_store를 사용한다.
        """
