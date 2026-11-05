"""수집 한 주기 — RSS(섹션별) + 검색어 탭 → 관련성 → 저장 → 규칙 판정.

- 메인은 AI 섹션(연구소 블로그·논문·릴리스·해설·커뮤니티·국내 AI 매체), 부록은 경제 섹션(경제 언론).
- 검색어 탭은 자기 섹션에서 이번 주기에 들어온 RSS 글을 관련성으로 고른다. 경제 탭은 뉴스 검색 API 결과도 더한다.
- 규칙 판정(AI 배지)은 한국어 뉴스 기사 묶음만 한다(domain/sections.should_judge). 판정하지 않는 묶음은
  본문도 저장하지 않는다 — 본문은 판정에만 쓰고 화면·API 로 내보내지 않는다.
- 원문 페이지는 가져오지 않는다(저장소 저작권 원칙, google_news_scraper 와 같음).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from news.app.dtos.news_dtos import (
    CollectReport,
    FeedSource,
    FetchedArticle,
    StoredArticle,
    VerdictCommand,
)
from news.app.ports.input.news_use_cases import NewsCollectUseCase
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.app.ports.output.news_source_ports import FeedReaderPort, NewsSearchPort
from news.domain.ai_filter import classify, load_thresholds
from news.domain.relevance import is_relevant, relevance
from news.domain.sections import should_judge
from news.domain.url import canonical_url

logger = logging.getLogger(__name__)

RULES_LAYER = "rules"
SEARCH_SECTION = "economy"  # 뉴스 검색 API 는 국내 기사라 경제 탭에만 쓴다


class NewsCollectInteractor(NewsCollectUseCase):
    def __init__(
        self,
        repository: NewsRepositoryPort,
        search: NewsSearchPort,
        feed_reader: FeedReaderPort,
        feeds: Sequence[FeedSource],
    ) -> None:
        self._repository = repository
        self._search = search
        self._feed_reader = feed_reader
        self._feeds = list(feeds)

    async def collect_once(self) -> CollectReport:
        report = CollectReport()
        picked: list[tuple[FetchedArticle, int | None, float]] = []  # (기사, 탭 id, 관련성)

        feed_items: list[FetchedArticle] = []
        for feed in self._feeds:
            report.feeds += 1
            try:
                feed_items.extend(await self._feed_reader.read(feed))
            except Exception as e:  # 한 피드 실패가 주기 전체를 멈추지 않게
                report.errors.append(f"RSS 실패 {feed.name}: {e}")
        picked.extend((item, None, 1.0) for item in feed_items)

        topics = await self._repository.list_topics(public_only=False, active_only=True)
        report.topics = len(topics)
        for topic in topics:
            for item in feed_items:
                if item.section != topic.section:
                    continue
                score = relevance(topic.query, item.title, item.summary)
                if is_relevant(score):
                    picked.append((item, topic.id, score))

        search_topics = [t for t in topics if t.section == SEARCH_SECTION]
        if search_topics and not self._search.enabled:
            report.errors.append("검색 API 키 없음 — 경제 검색어 탭의 뉴스 검색을 건너뜀")
        elif search_topics:
            for topic in search_topics:
                try:
                    items = await self._search.search(topic.query)
                except Exception as e:
                    report.errors.append(f"검색 실패 {topic.query!r}: {e}")
                    continue
                for item in items:
                    score = relevance(topic.query, item.title, item.summary)
                    if not is_relevant(score):
                        report.irrelevant += 1
                        continue
                    tagged = replace(item, section=SEARCH_SECTION, group="search")
                    picked.append((tagged, topic.id, score))
        report.fetched = len(picked)

        # 같은 주소는 한 번만 저장한다 (여러 검색어·피드에 함께 걸려도). 먼저 온 RSS 묶음을 남기고,
        # 검색과 RSS 에 함께 걸리면 RSS 쪽을 남긴다 — '최신' 목록(origin=feed)에서 빠지지 않게
        unique: dict[str, FetchedArticle] = {}
        for item, _, _ in picked:
            key = canonical_url(item.url)
            have = unique.get(key)
            if have is None or (have.origin != "feed" and item.origin == "feed"):
                unique[key] = item if should_judge(item.group) else replace(item, body="")
        stored = await self._repository.save_articles(list(unique.values()))
        report.new_articles = sum(1 for s in stored if s.is_new)
        by_url = {s.url: s for s in stored}

        links: dict[int, dict[int, float]] = {}
        for item, topic_id, score in picked:
            saved = by_url.get(canonical_url(item.url))
            if topic_id is None or saved is None:
                continue
            best = links.setdefault(topic_id, {})
            best[saved.id] = max(score, best.get(saved.id, 0.0))
        for topic_id, pairs in links.items():
            await self._repository.link_topic_articles(topic_id, list(pairs.items()))

        await self._judge(stored, report)
        return report

    async def _judge(self, stored: Sequence[StoredArticle], report: CollectReport) -> None:
        in_scope = [s for s in stored if should_judge(s.group)]
        report.not_judged = sum(1 for s in stored if s.is_new and not should_judge(s.group))
        version = str(load_thresholds()["harness_version"])
        missing = await self._repository.missing_verdicts(
            [s.id for s in in_scope], version, RULES_LAYER
        )
        targets = [s for s in in_scope if s.id in missing]
        if not targets:
            return
        rows: list[dict[str, Any]] = [
            {
                "id": s.id,
                "title": s.title,
                "summary": s.summary,
                "body": s.body,
                "url": s.url,
                "source": s.source_name or "",
                "author": s.author,
            }
            for s in targets
        ]
        # 교차 보도 묶음 계산이 O(n²)라 이벤트 루프를 막지 않게 스레드로 돌린다(§E.4)
        results = await asyncio.to_thread(classify, rows, "C")
        commands = [
            VerdictCommand(
                article_id=int(r["id"]),
                layer=RULES_LAYER,
                harness_version=version,
                verdict=str(r["verdict"]),
                badge=str(r["badge"]),
                reasons_ko=list(r["reasons_ko"]),
                signals=list(r["signals"]),
            )
            for r in results
        ]
        await self._repository.save_verdicts(commands)
        report.judged = len(commands)
        for c in commands:
            report.verdicts[c.verdict] = report.verdicts.get(c.verdict, 0) + 1
