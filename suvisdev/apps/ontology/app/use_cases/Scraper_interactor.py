"""사이트 1곳 + 키워드로 레코드를 수집해 JSONL로 저장하는 유스케이스.

크롤링(URL 발견)과 스크래핑(본문 추출)을 사이트별 SiteScraperPort 구현체가 한 번에
담당한다 — 사이트마다 검색 결과 구조가 달라서, 두 단계로 강제 분리하면 오히려 사이트
어댑터 하나하나가 더 복잡해진다. 이 인터랙터는 흐름만 조율한다: site_scraper.search()
제너레이터를 DatasetWriterPort로 그대로 흘려보내 한 건씩 즉시 저장하고, ScrapeSession으로
상태 전이를 기록한다.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ontology.app.dtos.scrape_dto import DatasetMeta, ScrapeTarget
from ontology.app.ports.input.scrape_dataset_use_case import ScrapeDatasetUseCase
from ontology.app.ports.output.dataset_writer_port import DatasetWriterPort
from ontology.app.ports.output.site_scraper_port import SiteScraperPort
from ontology.domain.scrape_session import ScrapeSession

logger = logging.getLogger(__name__)


class ScrapeDatasetInteractor(ScrapeDatasetUseCase):
    def __init__(self, *, scraper: SiteScraperPort, writer: DatasetWriterPort) -> None:
        self._scraper = scraper
        self._writer = writer

    def run(self, target: ScrapeTarget, *, limit: int, out_path: Path) -> DatasetMeta:
        session = ScrapeSession()
        session.start()
        try:
            records = self._scraper.search(target.keyword, limit)
            meta = self._writer.write(records, out_path)
        except Exception as e:
            session.fail(str(e))
            logger.warning(
                "[ScrapeDatasetInteractor] 수집 실패 | site=%s keyword=%s detail=%s",
                target.site_id,
                target.keyword,
                e,
            )
            raise

        session.finish()
        logger.info(
            "[ScrapeDatasetInteractor] 수집 완료 | site=%s keyword=%s records=%d path=%s",
            target.site_id,
            target.keyword,
            meta.record_count,
            meta.path,
        )
        return meta
