"""harvester CLI 컴포지션 루트.

FastAPI Depends가 아니라 일반 함수 조립이다 — CLI 실행에는 HTTP 요청 스코프가 없다.
Redis 어댑터(rate limiter, visited store)는 함수 안에서 지연 import한다 — 이 모듈
자체는 import 시점에 실제 사이트가 없어도(레지스트리가 비어 있어도) 항상 로드 가능해야
CLI의 `sites`/`interactive` 커맨드가 사이트 미등록 상태에서도 동작한다.
"""

from __future__ import annotations

from pathlib import Path

from ontology.adapter.outbound.scraper.registry import SITE_REGISTRY
from ontology.app.ports.input.crawl_schedule_use_case import CrawlScheduleUseCase
from ontology.app.ports.input.scrape_dataset_use_case import ScrapeDatasetUseCase
from ontology.app.ports.output.site_scraper_port import SiteScraperPort


class UnknownSiteError(Exception):
    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self.available = sorted(SITE_REGISTRY)
        super().__init__(f"등록되지 않은 사이트: {site_id} (등록됨: {', '.join(self.available) or '없음'})")


def build_site_scraper(site_id: str, *, rate: float, dedup: bool) -> SiteScraperPort:
    scraper_cls = SITE_REGISTRY.get(site_id)
    if scraper_cls is None:
        raise UnknownSiteError(site_id)

    from ontology.adapter.outbound.cache.noop_visited_store_adapter import (
        NoOpVisitedStoreAdapter,
    )
    from ontology.adapter.outbound.cache.redis_rate_limiter_adapter import (
        RedisRateLimiterAdapter,
    )
    from ontology.adapter.outbound.cache.redis_visited_store_adapter import (
        RedisVisitedStoreAdapter,
    )
    from ontology.adapter.outbound.http.httpx_page_fetcher_adapter import (
        HttpxPageFetcherAdapter,
    )

    fetcher = (
        HttpxPageFetcherAdapter(user_agent=scraper_cls.user_agent)
        if scraper_cls.user_agent
        else HttpxPageFetcherAdapter()
    )
    rate_limiter = RedisRateLimiterAdapter(interval_seconds=rate)
    visited_store = RedisVisitedStoreAdapter() if dedup else NoOpVisitedStoreAdapter()
    return scraper_cls(fetcher=fetcher, rate_limiter=rate_limiter, visited_store=visited_store)


def build_scrape_dataset_use_case(scraper: SiteScraperPort) -> ScrapeDatasetUseCase:
    from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E501
        LocalJsonlDatasetRepository,
    )
    from ontology.app.use_cases.Scraper_interactor import ScrapeDatasetInteractor

    return ScrapeDatasetInteractor(scraper=scraper, writer=LocalJsonlDatasetRepository())


def build_crawl_schedule_use_case(
    *, rate: float = 1.0, limit_per_keyword: int = 100
) -> CrawlScheduleUseCase:
    """crawl-batch(cron 진입점) 컴포지션. dedup은 항상 True — 증분 수집이 이 배치의 목적이다."""
    from ontology.adapter.outbound.cache.redis_crawl_schedule_state_adapter import (
        RedisCrawlScheduleStateAdapter,
    )
    from ontology.adapter.outbound.config.yaml_crawl_policy_adapter import (
        YamlCrawlPolicyAdapter,
    )
    from ontology.adapter.outbound.events.log_crawl_event_publisher_adapter import (
        LogCrawlEventPublisherAdapter,
    )
    from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E501
        LocalJsonlDatasetRepository,
    )
    from ontology.app.use_cases.Crawler_interactor import CrawlScheduleInteractor

    def _build_scraper(site_id: str) -> SiteScraperPort:
        return build_site_scraper(site_id, rate=rate, dedup=True)

    return CrawlScheduleInteractor(
        policies=YamlCrawlPolicyAdapter(),
        schedule_state=RedisCrawlScheduleStateAdapter(),
        build_scraper=_build_scraper,
        writer=LocalJsonlDatasetRepository(),
        event_publisher=LogCrawlEventPublisherAdapter(),
        output_dir=Path("datasets") / "crawl",
        limit_per_keyword=limit_per_keyword,
    )
