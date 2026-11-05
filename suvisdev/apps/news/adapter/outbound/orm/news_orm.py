"""news.suvisdev.cloud 테이블 (2026-11-05). ERD: apps/news/_docs/CLAUDE.md"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from news.adapter.outbound.orm.base import NewsBase

_JSON = JSON().with_variant(JSONB(), "postgresql")


class NewsTopicOrm(NewsBase):
    """운영자가 저장한 검색어 = 화면의 탭."""

    __tablename__ = "news_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(100), unique=True)
    label: Mapped[str] = mapped_column(String(50))
    section: Mapped[str] = mapped_column(String(16), server_default="ai")  # ai | economy
    is_public: Mapped[bool] = mapped_column(Boolean, server_default=true())
    active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsArticleOrm(NewsBase):
    """수집한 기사. 본문(body)은 RSS 가 직접 준 것만 — 원문 페이지는 가져오지 않는다. 화면·API 로 내보내지 않는다."""

    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_articles_origin_sort_at", "origin", "sort_at"),
        Index("ix_news_articles_section_sort_at", "section", "sort_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    canonical_url: Mapped[str] = mapped_column(String(1000), unique=True)
    link: Mapped[str | None] = mapped_column(String(1000))
    source_domain: Mapped[str] = mapped_column(String(200), index=True)
    source_name: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, server_default="")
    body: Mapped[str] = mapped_column(Text, server_default="")
    author: Mapped[str] = mapped_column(String(100), server_default="")
    origin: Mapped[str] = mapped_column(String(16))  # "search" | "feed"
    section: Mapped[str] = mapped_column(String(16), server_default="ai")  # ai | economy
    feed_group: Mapped[str] = mapped_column(String(16), server_default="")  # domain/sections.GROUPS
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsTopicArticleOrm(NewsBase):
    __tablename__ = "news_topic_articles"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("news_topics.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    relevance: Mapped[float] = mapped_column(Float)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsVerdictOrm(NewsBase):
    """판정. 층(layer)마다 1건 — rules(규칙) · llm(올라마 2차). 화면은 llm 이 있으면 llm, 없으면 rules."""

    __tablename__ = "news_verdicts"
    __table_args__ = (
        UniqueConstraint("article_id", "layer", name="uq_news_verdicts_article_layer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id", ondelete="CASCADE"))
    layer: Mapped[str] = mapped_column(String(16))
    harness_version: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str] = mapped_column(String(16))  # normal | pending | ai
    badge: Mapped[str] = mapped_column(String(16))  # none | ai_disclosed | ai_suspected
    reasons_ko: Mapped[list[str]] = mapped_column(_JSON)
    signals: Mapped[list[dict[str, Any]]] = mapped_column(_JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
