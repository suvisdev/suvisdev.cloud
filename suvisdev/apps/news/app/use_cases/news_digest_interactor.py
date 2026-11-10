"""아침 메일 한 번 — 어제 AI 글을 분류해 기술 소식만 골라 보낸다(11-09)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from news.app.dtos.news_dtos import ArticleDto
from news.app.ports.output.news_digest_ports import (
    ArticleClassifierPort,
    ClassifierUnavailableError,
    DigestLedgerPort,
    DigestMailerPort,
)
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.domain.digest import (
    DigestItem,
    digest_day,
    digest_window,
    is_due,
    render_digest,
    select_items,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestReport:
    status: str  # not_due·skipped·model_unavailable·mail_failed·no_items·sent
    candidates: int = 0
    tech: int = 0
    sent: int = 0


def _item(article: ArticleDto, value: int = 1) -> DigestItem:
    return DigestItem(
        title=article.title_ko or article.title,
        url=article.url,
        group=article.group,
        source=article.source_name or article.source_domain,
        summary=article.summary_ko or "",
        hot_label=article.hot_label,
        sort_at=article.sort_at,
        value=value,
    )


class NewsDigestInteractor:
    def __init__(
        self,
        repository: NewsRepositoryPort,
        classifier: ArticleClassifierPort,
        mailer: DigestMailerPort,
        ledger: DigestLedgerPort,
    ) -> None:
        self._repository = repository
        self._classifier = classifier
        self._mailer = mailer
        self._ledger = ledger

    async def send_if_due(self, now: datetime) -> DigestReport:
        if not is_due(now):
            return DigestReport("not_due")
        day = digest_day(now)
        if not await asyncio.to_thread(self._ledger.begin, day):
            return DigestReport("skipped")

        since, until = digest_window(day)
        candidates = await self._repository.list_digest_candidates(since=since, until=until)
        tech: list[DigestItem] = []
        try:
            for article in candidates:
                judgement = await self._classifier.classify(article)
                if judgement is not None and judgement.label == "tech":
                    tech.append(_item(article, judgement.value))
        except ClassifierUnavailableError as e:
            logger.warning("[news] 메일 분류 모델 응답 없음 — 다음 주기에 다시: %s", e)
            return DigestReport("model_unavailable", len(candidates))

        items = select_items(tech)
        if not items:
            await asyncio.to_thread(self._ledger.finish, day)
            return DigestReport("no_items", len(candidates))

        subject, text, html = render_digest(day, items)
        try:
            await asyncio.to_thread(self._mailer.send, subject=subject, text=text, html=html)
        except OSError as e:  # smtplib 예외는 OSError 계열
            logger.warning("[news] 메일 발송 실패 — 다음 주기에 다시: %s", type(e).__name__)
            await asyncio.to_thread(self._ledger.record_failure, day)
            return DigestReport("mail_failed", len(candidates), len(tech))
        await asyncio.to_thread(self._ledger.finish, day)
        return DigestReport("sent", len(candidates), len(tech), len(items))
