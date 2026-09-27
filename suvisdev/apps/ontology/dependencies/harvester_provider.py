"""harvester CLI 컴포지션 루트.

FastAPI Depends가 아니라 일반 함수 조립이다 — CLI 실행에는 HTTP 요청 스코프가 없다.
Redis 어댑터(rate limiter, visited store)는 함수 안에서 지연 import한다 — 이 모듈
자체는 import 시점에 실제 사이트가 없어도(레지스트리가 비어 있어도) 항상 로드 가능해야
CLI의 `sites`/`interactive` 커맨드가 사이트 미등록 상태에서도 동작한다.
"""

from __future__ import annotations

import time
from pathlib import Path

from ontology.adapter.outbound.scraper.registry import SITE_REGISTRY
from ontology.app.ports.input.crawl_schedule_use_case import CrawlScheduleUseCase
from ontology.app.ports.input.custom_url_scrape_use_case import CustomUrlScrapeUseCase
from ontology.app.ports.input.scrape_dataset_use_case import ScrapeDatasetUseCase
from ontology.app.ports.output.crawl_policy_port import CrawlPolicyPort
from ontology.app.ports.output.crawl_schedule_state_port import CrawlScheduleStatePort
from ontology.app.ports.output.harvester_command_parser_port import HarvesterCommandParserPort
from ontology.app.ports.output.keyword_source_port import KeywordSourcePort
from ontology.app.ports.output.site_scraper_port import SiteScraperPort


class UnknownSiteError(Exception):
    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self.available = sorted(SITE_REGISTRY)
        super().__init__(
            f"등록되지 않은 사이트: {site_id} (등록됨: {', '.join(self.available) or '없음'})"
        )


class UnknownKeywordSourceError(Exception):
    def __init__(self, source_id: str) -> None:
        from ontology.adapter.outbound.scraper.keyword_source_registry import (
            KEYWORD_SOURCE_REGISTRY,
        )

        self.source_id = source_id
        self.available = sorted(KEYWORD_SOURCE_REGISTRY)
        super().__init__(
            f"등록되지 않은 동적 키워드 소스: {source_id} (등록됨: {', '.join(self.available) or '없음'})"
        )


_CRAWLED_OUTPUT_DIR = Path("apps") / "ontology" / "resources" / "crawled"


def default_scrape_out_path(site_id: str, keyword: str) -> Path:
    date = time.strftime("%Y%m%d")
    safe_keyword = keyword.replace("/", "_").replace(" ", "_")
    return Path("datasets") / f"{site_id}_{safe_keyword}_{date}.jsonl"


def custom_url_scrape_out_path(url: str) -> Path:
    from urllib.parse import urlparse

    date = time.strftime("%Y%m%d")
    domain = urlparse(url).netloc.replace(":", "_") or "custom"
    # 크롤러 탭의 custom_{날짜}.jsonl(도메인 구분 없음, append)과는 파일명이 겹치지
    # 않는다 — 같은 폴더에 둬도 서로 안 건드림.
    return _CRAWLED_OUTPUT_DIR / f"custom_{domain}_{date}.jsonl"


def custom_url_crawl_out_path() -> Path:
    date = time.strftime("%Y%m%d")
    return _CRAWLED_OUTPUT_DIR / f"custom_{date}.jsonl"


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


def build_keyword_source(source_id: str, *, rate: float) -> KeywordSourcePort:
    from ontology.adapter.outbound.cache.redis_rate_limiter_adapter import (
        RedisRateLimiterAdapter,
    )
    from ontology.adapter.outbound.http.httpx_page_fetcher_adapter import (
        HttpxPageFetcherAdapter,
    )
    from ontology.adapter.outbound.scraper.keyword_source_registry import (
        KEYWORD_SOURCE_REGISTRY,
    )

    source_cls = KEYWORD_SOURCE_REGISTRY.get(source_id)
    if source_cls is None:
        raise UnknownKeywordSourceError(source_id)

    return source_cls(
        fetcher=HttpxPageFetcherAdapter(),
        rate_limiter=RedisRateLimiterAdapter(interval_seconds=rate),
    )


def build_scrape_dataset_use_case(scraper: SiteScraperPort) -> ScrapeDatasetUseCase:
    from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E501
        LocalJsonlDatasetRepository,
    )
    from ontology.app.use_cases.Scraper_interactor import ScrapeDatasetInteractor

    return ScrapeDatasetInteractor(scraper=scraper, writer=LocalJsonlDatasetRepository())


def build_crawl_policy_port() -> CrawlPolicyPort:
    """크롤링 탭(읽기 전용 정책 현황판)이 재사용하는, 정책 어댑터만 단독 노출."""
    from ontology.adapter.outbound.config.yaml_crawl_policy_adapter import (
        YamlCrawlPolicyAdapter,
    )

    return YamlCrawlPolicyAdapter()


def build_crawl_schedule_state_port() -> CrawlScheduleStatePort:
    """크롤링 탭이 site별 마지막 실행 시각을 읽기 위해 재사용하는 단독 노출."""
    from ontology.adapter.outbound.cache.redis_crawl_schedule_state_adapter import (
        RedisCrawlScheduleStateAdapter,
    )

    return RedisCrawlScheduleStateAdapter()


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

    def _build_keyword_source(source_id: str) -> KeywordSourcePort:
        return build_keyword_source(source_id, rate=rate)

    return CrawlScheduleInteractor(
        policies=YamlCrawlPolicyAdapter(),
        schedule_state=RedisCrawlScheduleStateAdapter(),
        build_scraper=_build_scraper,
        writer=LocalJsonlDatasetRepository(),
        event_publisher=LogCrawlEventPublisherAdapter(),
        output_dir=_CRAWLED_OUTPUT_DIR,
        limit_per_keyword=limit_per_keyword,
        build_keyword_source=_build_keyword_source,
    )


def build_ai_review_generator() -> object:
    """AI 리뷰 생성 인터랙터 조립 — CLI에서 호출."""
    from ontology.adapter.outbound.llm.gemini_llm_adapter import GeminiLlmAdapter
    from ontology.adapter.outbound.repositories.ai_review_pg_adapter import AiReviewPgAdapter
    from ontology.app.use_cases.ai_review_generator_interactor import (
        AiReviewGeneratorInteractor,
    )

    return AiReviewGeneratorInteractor(
        llm=GeminiLlmAdapter(),
        writer=AiReviewPgAdapter(),
    )


def build_harvester_command_parser() -> HarvesterCommandParserPort:
    from ontology.adapter.outbound.llm.exaone_small_llm_adapter import ExaoneSmallLlmAdapter
    from ontology.adapter.outbound.llm.llm_harvester_command_parser import (
        LlmHarvesterCommandParser,
    )

    return LlmHarvesterCommandParser(llm=ExaoneSmallLlmAdapter())


def build_custom_url_scrape_use_case() -> CustomUrlScrapeUseCase:
    """등록된 사이트 밖의 임의 URL + 자연어 지시 수집 컴포지션."""
    from ontology.adapter.outbound.http.httpx_page_fetcher_adapter import HttpxPageFetcherAdapter
    from ontology.adapter.outbound.http.robots_checker_adapter import HttpxRobotsCheckerAdapter
    from ontology.adapter.outbound.llm.gemini_llm_adapter import GeminiLlmAdapter
    from ontology.adapter.outbound.llm.gemini_page_extractor import GeminiPageExtractorAdapter
    from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E501
        LocalJsonlDatasetRepository,
    )
    from ontology.app.use_cases.custom_url_scrape_interactor import CustomUrlScrapeInteractor

    fetcher = HttpxPageFetcherAdapter()
    return CustomUrlScrapeInteractor(
        fetcher=fetcher,
        robots_checker=HttpxRobotsCheckerAdapter(fetcher=fetcher),
        extractor=GeminiPageExtractorAdapter(llm=GeminiLlmAdapter()),
        writer=LocalJsonlDatasetRepository(),
    )
