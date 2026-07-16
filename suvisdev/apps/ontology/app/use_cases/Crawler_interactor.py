"""crawl_config.yaml에 등록된 사이트를 주기적으로(cron 진입점) 증분 수집하는 배치 유스케이스.

ScrapeDatasetInteractor(1회성 CLI 수집)와 수집 로직을 공유한다 — 여기서 새로 구현하는
건 "여러 정책 순회 + due 체크 + 증분(dedup) + 누적 저장 + 이벤트 발행" 조율뿐이고,
실제 검색/추출은 그대로 SiteScraperPort.search()를 재사용한다. 증분 수집은 각 사이트
어댑터가 내부적으로 VisitedStorePort를 확인하기 때문에 여기서 별도 dedup 로직이
필요 없다 — DI가 dedup=True로 조립한 스크래퍼를 주입해주기만 하면 된다.

키워드 여러 개를 한 정책에서 순회할 때도 itertools.chain으로 지연 연결해 스트리밍을
유지한다 (리스트로 전부 모았다가 한 번에 쓰지 않는다 — harvester 스펙의 금지 사항).
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ontology.app.dtos.crawl_schedule_dto import CrawlPolicy
from ontology.app.dtos.scrape_dto import DatasetMeta
from ontology.app.ports.input.crawl_schedule_use_case import CrawlScheduleUseCase
from ontology.app.ports.output.crawl_event_publisher_port import CrawlEventPublisherPort
from ontology.app.ports.output.crawl_policy_port import CrawlPolicyPort
from ontology.app.ports.output.crawl_schedule_state_port import CrawlScheduleStatePort
from ontology.app.ports.output.dataset_writer_port import DatasetWriterPort
from ontology.app.ports.output.keyword_source_port import KeywordSourcePort
from ontology.app.ports.output.site_scraper_port import SiteScraperPort
from ontology.domain.events.spoke_events import CrawlCompletedEvent

logger = logging.getLogger(__name__)


class CrawlScheduleInteractor(CrawlScheduleUseCase):
    def __init__(
        self,
        *,
        policies: CrawlPolicyPort,
        schedule_state: CrawlScheduleStatePort,
        build_scraper: Callable[[str], SiteScraperPort],
        writer: DatasetWriterPort,
        event_publisher: CrawlEventPublisherPort,
        output_dir: Path,
        limit_per_keyword: int = 100,
        build_keyword_source: Callable[[str], KeywordSourcePort] | None = None,
        max_dynamic_keywords: int = 20,
    ) -> None:
        self._policies = policies
        self._schedule_state = schedule_state
        self._build_scraper = build_scraper
        self._writer = writer
        self._event_publisher = event_publisher
        self._output_dir = output_dir
        self._limit_per_keyword = limit_per_keyword
        self._build_keyword_source = build_keyword_source
        self._max_dynamic_keywords = max_dynamic_keywords

    def run_due_batches(self, *, now: datetime | None = None) -> list[DatasetMeta]:
        now = now or datetime.now(UTC)
        results: list[DatasetMeta] = []
        for policy in self._policies.get_policies():
            if not self._is_due(policy, now):
                continue
            results.append(self._run_policy(policy, now))
            self._schedule_state.set_last_run(policy.site_id, now)
        return results

    def run_once(self, *, site_id: str, keywords: tuple[str, ...], limit: int) -> DatasetMeta:
        """어드민 화면 등에서 즉시 1회 실행 — crawl_config.yaml/due-check를 거치지 않는다.

        같은 append+이벤트 발행 경로(_run_policy)를 그대로 재사용한다 — interval_minutes는
        due-check에 안 쓰이므로 아무 값이나 넣어도 무방하다.
        """
        policy = CrawlPolicy(site_id=site_id, keywords=keywords, interval_minutes=1, limit_per_keyword=limit)
        return self._run_policy(policy, datetime.now(UTC))

    def _is_due(self, policy: CrawlPolicy, now: datetime) -> bool:
        last_run = self._schedule_state.get_last_run(policy.site_id)
        if last_run is None:
            return True
        return now - last_run >= timedelta(minutes=policy.interval_minutes)

    def _run_policy(self, policy: CrawlPolicy, now: datetime) -> DatasetMeta:
        keywords = self._resolve_keywords(policy)
        scraper = self._build_scraper(policy.site_id)
        limit = policy.limit_per_keyword or self._limit_per_keyword
        records = itertools.chain.from_iterable(scraper.search(keyword, limit) for keyword in keywords)
        path = self._output_dir / f"{policy.site_id}_{now.strftime('%Y%m%d')}.jsonl"
        meta = self._writer.write(records, path, append=True)

        self._event_publisher.publish(
            CrawlCompletedEvent(
                site_id=policy.site_id,
                keyword_count=len(keywords),
                record_count=meta.record_count,
                jsonl_path=meta.path,
                completed_at=now,
            )
        )
        logger.info(
            "[CrawlScheduleInteractor] 배치 완료 | site=%s keywords=%d records=%d path=%s",
            policy.site_id,
            len(keywords),
            meta.record_count,
            meta.path,
        )
        return meta

    def _resolve_keywords(self, policy: CrawlPolicy) -> tuple[str, ...]:
        """정적 keywords + keyword_source.resolve()(있으면) 병합, 중복 제거, 상한 적용.

        resolve() 실패는 이 소스만 건너뛰고 정적 키워드로 배치를 계속한다 — 배치 전체를
        막을 이유가 없다(다른 정책·다른 사이트는 이 소스와 무관하므로).
        """
        keywords = list(policy.keywords)
        if not policy.keyword_source or self._build_keyword_source is None:
            return tuple(keywords)

        try:
            source = self._build_keyword_source(policy.keyword_source)
            dynamic = source.resolve()
        except Exception as e:  # noqa: BLE001 - 플러그인 경계, 배치 중단시키면 안 됨
            logger.warning(
                "[CrawlScheduleInteractor] keyword_source 실패, 정적 키워드만 사용 | "
                "source=%s detail=%s",
                policy.keyword_source,
                e,
            )
            return tuple(keywords)

        if len(dynamic) > self._max_dynamic_keywords:
            logger.warning(
                "[CrawlScheduleInteractor] 동적 키워드 %d개 → 상한 %d개로 자름 | source=%s",
                len(dynamic),
                self._max_dynamic_keywords,
                policy.keyword_source,
            )
            dynamic = dynamic[: self._max_dynamic_keywords]

        for kw in dynamic:
            if kw not in keywords:
                keywords.append(kw)
        return tuple(keywords)
