"""CrawlScheduleInteractor 테스트용 인메모리 fake 모음 — 네트워크·Redis 없이 동작한다."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from ontology.app.dtos.crawl_schedule_dto import CrawlPolicy
from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.crawl_event_publisher_port import CrawlEventPublisherPort
from ontology.app.ports.output.crawl_policy_port import CrawlPolicyPort
from ontology.app.ports.output.crawl_schedule_state_port import CrawlScheduleStatePort
from ontology.app.ports.output.site_scraper_port import SiteScraperPort
from ontology.app.ports.output.visited_store_port import VisitedStorePort
from ontology.domain.events.spoke_events import CrawlCompletedEvent


class FakeCrawlPolicyPort(CrawlPolicyPort):
    def __init__(self, policies: list[CrawlPolicy]) -> None:
        self._policies = policies

    def get_policies(self) -> list[CrawlPolicy]:
        return self._policies


class FakeCrawlScheduleStatePort(CrawlScheduleStatePort):
    def __init__(self) -> None:
        self._last_run: dict[str, datetime] = {}

    def get_last_run(self, site_id: str) -> datetime | None:
        return self._last_run.get(site_id)

    def set_last_run(self, site_id: str, at: datetime) -> None:
        self._last_run[site_id] = at


class FakeCrawlEventPublisher(CrawlEventPublisherPort):
    def __init__(self) -> None:
        self.published: list[CrawlCompletedEvent] = []

    def publish(self, event: CrawlCompletedEvent) -> None:
        self.published.append(event)


class FakeVisitedStore(VisitedStorePort):
    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def is_visited(self, keyword: str, url: str) -> bool:
        return (keyword, url) in self._seen

    def mark(self, keyword: str, url: str) -> None:
        self._seen.add((keyword, url))


class FakeDedupingSiteScraper(SiteScraperPort):
    """search() 호출 때마다 항상 같은 3개 URL을 "발견"하지만, visited_store에 이미
    있으면 걸러낸다 — 두 번째 실행부터는 새로 생긴 게 없으면 아무것도 안 나온다."""

    site_id = "fake-dedup"

    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        for i in range(min(limit, 3)):
            url = f"https://fake-dedup.test/{keyword}/{i}"
            if self._visited_store.is_visited(keyword, url):
                continue
            self._visited_store.mark(keyword, url)
            yield ScrapedRecord(
                source=self.site_id,
                keyword=keyword,
                url=url,
                title=f"{keyword} {i}",
                content="content",
                author_hash="abcd1234",
                scraped_at=datetime.now(),
            )
