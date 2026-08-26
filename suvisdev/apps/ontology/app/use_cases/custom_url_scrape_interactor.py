"""임의 URL + 자연어 지시 스크랩 — ScrapeDatasetInteractor/CrawlScheduleInteractor와
달리 SiteScraperPort(키워드 검색 계약)에 안 맞아서(URL이 요청마다 사용자 입력으로
바뀌고 "검색"이 아니라 "지시"라서) 별도 인터랙터로 둔다. 대신 DatasetWriterPort·
ScrapedRecord는 그대로 재사용해 저장 방식이 갈라지지 않게 한다.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from ontology.app.dtos.scrape_dto import DatasetMeta, ScrapedRecord
from ontology.app.ports.input.custom_url_scrape_use_case import CustomUrlScrapeUseCase
from ontology.app.ports.output.crawl_errors import CrawlFetchError
from ontology.app.ports.output.dataset_writer_port import DatasetWriterPort
from ontology.app.ports.output.page_extractor_port import PageExtractorPort
from ontology.app.ports.output.page_fetcher_port import PageFetcherPort
from ontology.app.ports.output.robots_checker_port import RobotsCheckerPort

logger = logging.getLogger(__name__)


class CustomUrlScrapeInteractor(CustomUrlScrapeUseCase):
    def __init__(
        self,
        *,
        fetcher: PageFetcherPort,
        robots_checker: RobotsCheckerPort,
        extractor: PageExtractorPort,
        writer: DatasetWriterPort,
    ) -> None:
        self._fetcher = fetcher
        self._robots_checker = robots_checker
        self._extractor = extractor
        self._writer = writer

    async def run(
        self, *, url: str, instruction: str, out_path: Path, append: bool = False
    ) -> DatasetMeta:
        # extractor(LLM 호출)만 원래 async고 나머지는 동기 포트라, 이벤트 루프가 안 막히게
        # 동기 호출들만 asyncio.to_thread로 감싼다.
        allowed = await asyncio.to_thread(self._robots_checker.is_allowed, url)
        if not allowed:
            raise CrawlFetchError(
                f"robots.txt가 이 URL의 수집을 금지합니다: {url}", status_code=403
            )

        html = await asyncio.to_thread(self._fetcher.fetch, url)
        extracted = await self._extractor.extract(html, instruction)

        record = ScrapedRecord(
            source="custom",
            keyword=instruction[:80],
            url=url,
            title=extracted.title,
            content=extracted.content,
            author_hash=hashlib.sha256(url.encode()).hexdigest()[:8],
            scraped_at=datetime.now(UTC),
        )
        meta = await asyncio.to_thread(self._writer.write, iter([record]), out_path, append=append)
        logger.info(
            "[CustomUrlScrapeInteractor] 완료 | url=%s instruction=%s path=%s",
            url,
            instruction[:80],
            meta.path,
        )
        return meta
