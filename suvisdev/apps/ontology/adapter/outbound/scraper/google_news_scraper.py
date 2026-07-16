"""구글 뉴스 RSS 검색 피드 어댑터 — CrawlScheduleInteractor(배치)가 쓰는 크롤러.

기사 원문 페이지는 절대 follow-fetch하지 않는다 — 저작권 문제로 제목+요약+링크까지만
수집한다(피드 자체가 이미 그 셋만 준다). RSS는 같은 기사가 여러 배치에 걸쳐 피드에
남아있으므로 VisitedStorePort dedup(키=link, 정규화 없음)이 사실상 필수 경로다.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import quote

import feedparser
from bs4 import BeautifulSoup

from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.site_scraper_port import SiteScraperPort

_FEED_URL = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
_RATE_DOMAIN = "news.google.com"


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


class GoogleNewsScraper(SiteScraperPort):
    site_id = "google_news"

    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        self._rate_limiter.acquire(_RATE_DOMAIN)  # 피드 1회 fetch — 요청 자체는 1건
        url = _FEED_URL.format(query=quote(keyword))
        xml = self._fetcher.fetch(url)
        parsed = feedparser.parse(xml)

        yielded = 0
        for entry in parsed.entries:
            if yielded >= limit:
                break
            link = entry.link
            if self._visited_store.is_visited(keyword, link):
                continue
            self._visited_store.mark(keyword, link)

            publisher = entry.source.get("title", "") if entry.get("source") else ""
            summary = _strip_html(entry.get("summary", ""))
            published_at = None
            pp = entry.get("published_parsed")
            if pp:
                published_at = datetime(pp[0], pp[1], pp[2], pp[3], pp[4], pp[5], tzinfo=UTC)

            yield ScrapedRecord(
                source=self.site_id,
                keyword=keyword,
                url=link,
                title=entry.title,
                content=f"{entry.title}\n{summary}".strip(),
                author_hash=hashlib.sha256(publisher.encode()).hexdigest()[:8],
                scraped_at=datetime.now(UTC),
                published_at=published_at,
                publisher=publisher or None,
                summary=summary or None,
            )
            yielded += 1
