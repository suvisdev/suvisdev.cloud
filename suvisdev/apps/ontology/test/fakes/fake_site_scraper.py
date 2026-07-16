"""테스트 전용 SiteScraperPort — 네트워크·Redis 없이 결정론적 레코드를 만든다."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime

from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.site_scraper_port import SiteScraperPort


class FakeSiteScraper(SiteScraperPort):
    site_id = "fake"

    def __init__(self) -> None:
        pass  # 진짜 fetcher/rate_limiter/visited_store가 필요 없는 순수 fake

    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        for i in range(limit):
            url = f"https://fake.test/{keyword}/{i}"
            yield ScrapedRecord(
                source=self.site_id,
                keyword=keyword,
                url=url,
                title=f"{keyword} 리뷰 {i}",
                content=f"{keyword}에 대한 가짜 리뷰 본문 {i}",
                rating=4.0,
                author_hash=hashlib.sha256(f"author-{i}".encode()).hexdigest()[:8],
                scraped_at=datetime.now(UTC),
            )
