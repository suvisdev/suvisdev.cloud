"""crawl.completed 발행 — 지금은 로그만 남긴다.

star_craft(apps/ontology/_docs/star-craft-pipeline.md)가 아직 없어서(P1도 미착수)
실제로 보낼 HTTP 엔드포인트가 없다. star_craft의 POST /star-craft/events가 생기면
이 어댑터만 HTTP 발행으로 교체하면 된다 — CrawlScheduleInteractor는
CrawlEventPublisherPort만 알기 때문에 인터랙터·포트는 그대로 둔다.
"""

from __future__ import annotations

import logging

from ontology.app.ports.output.crawl_event_publisher_port import CrawlEventPublisherPort
from ontology.domain.events.spoke_events import CrawlCompletedEvent

logger = logging.getLogger(__name__)


class LogCrawlEventPublisherAdapter(CrawlEventPublisherPort):
    def publish(self, event: CrawlCompletedEvent) -> None:
        logger.info(
            "[crawl.completed] site=%s keywords=%d records=%d path=%s completed_at=%s",
            event.site_id,
            event.keyword_count,
            event.record_count,
            event.jsonl_path,
            event.completed_at.isoformat(),
        )
