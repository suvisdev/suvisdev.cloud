"""Spoke → Hub 이벤트 타입 정의."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DispatchEmailEvent:
    to: str
    prompt: str
    subject: str | None


@dataclass(frozen=True)
class InboundMessageEvent:
    """외부 채널(telegram·discord·email)로 인입된 메시지 이벤트."""

    channel: str
    sender: str
    body: str
    important_client: bool = False


@dataclass(frozen=True)
class CrawlCompletedEvent:
    """harvester crawl-batch 1개 정책 처리 완료 — star_craft 연동 대비(아직 미구현, 지금은
    LogCrawlEventPublisherAdapter가 로그만 남긴다. apps/ontology/_docs/star-craft-pipeline.md
    참고, 실제 HTTP 발행은 star_craft 앱이 만들어진 뒤의 몫)."""

    site_id: str
    keyword_count: int
    record_count: int
    jsonl_path: str
    completed_at: datetime
