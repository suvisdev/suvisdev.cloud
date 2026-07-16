from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ontology.app.ports.output.page_fetcher_port import PageFetcherPort
from ontology.app.ports.output.rate_limiter_port import RateLimiterPort


class KeywordSourcePort(ABC):
    """crawl_config.yaml의 keyword_source로 참조되는 동적 키워드 공급원.

    생성자를 여기서 고정해둔 이유는 SiteScraperPort와 같다 — harvester_provider가
    KEYWORD_SOURCE_REGISTRY에서 꺼낸 클래스를 fetcher/rate_limiter 두 개로 균일하게
    조립하기 때문이다.
    """

    source_id: ClassVar[str]

    def __init__(self, *, fetcher: PageFetcherPort, rate_limiter: RateLimiterPort) -> None:
        self._fetcher = fetcher
        self._rate_limiter = rate_limiter

    @abstractmethod
    def resolve(self) -> list[str]:
        """배치 시작 시점에 동적 키워드 목록을 반환한다."""
