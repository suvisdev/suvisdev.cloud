"""news 앱 DI. 라우터는 get_db 세션, 스케줄러는 세션 팩토리로 같은 인터랙터를 조립한다."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db, get_session_factory
from news.adapter.outbound.http.hot_sources import HackerNewsSource, HuggingFacePapersSource
from news.adapter.outbound.http.naver_news_search import NaverNewsSearchClient
from news.adapter.outbound.http.rss_feed_reader import RssFeedReader, load_latest_feeds
from news.adapter.outbound.kvstore.redis_digest_ledger import RedisDigestLedger
from news.adapter.outbound.llm.ollama_article_classifier import OllamaArticleClassifier
from news.adapter.outbound.llm.ollama_ko_summarizer import OllamaKoSummarizer
from news.adapter.outbound.mail.smtp_digest_mailer import SmtpDigestMailer
from news.adapter.outbound.pg.news_pg_repository import NewsPgRepository
from news.app.dtos.news_dtos import CollectReport, HotReport, SummaryReport
from news.app.ports.input.news_use_cases import (
    NewsCollectUseCase,
    NewsHotUseCase,
    NewsReadUseCase,
    NewsSummarizeUseCase,
    NewsTopicAdminUseCase,
)
from news.app.use_cases.news_collect_interactor import NewsCollectInteractor
from news.app.use_cases.news_digest_interactor import DigestReport, NewsDigestInteractor
from news.app.use_cases.news_hot_interactor import NewsHotInteractor
from news.app.use_cases.news_read_interactor import NewsReadInteractor
from news.app.use_cases.news_summarize_interactor import NewsSummarizeInteractor
from news.app.use_cases.news_topic_admin_interactor import NewsTopicAdminInteractor


def build_collect_use_case(session: AsyncSession) -> NewsCollectUseCase:
    return NewsCollectInteractor(
        repository=NewsPgRepository(session=session),
        search=NaverNewsSearchClient.from_env(),
        feed_reader=RssFeedReader(),
        feeds=load_latest_feeds(),
    )


def get_news_read_use_case(db: AsyncSession = Depends(get_db)) -> NewsReadUseCase:
    return NewsReadInteractor(repository=NewsPgRepository(session=db), feeds=load_latest_feeds())


def get_news_topic_admin_use_case(db: AsyncSession = Depends(get_db)) -> NewsTopicAdminUseCase:
    return NewsTopicAdminInteractor(repository=NewsPgRepository(session=db))


def get_news_collect_use_case(db: AsyncSession = Depends(get_db)) -> NewsCollectUseCase:
    return build_collect_use_case(db)


async def run_collect_once() -> CollectReport:
    """스케줄러용 — 요청 밖이라 세션을 직접 연다."""
    factory = get_session_factory()
    async with factory() as session:
        return await build_collect_use_case(session).collect_once()


def build_hot_use_case(session: AsyncSession) -> NewsHotUseCase:
    return NewsHotInteractor(
        repository=NewsPgRepository(session=session),
        sources=[HuggingFacePapersSource(), HackerNewsSource()],
    )


async def run_hot_once() -> HotReport:
    """스케줄러용 — 화제 수치 갱신."""
    factory = get_session_factory()
    async with factory() as session:
        return await build_hot_use_case(session).refresh()


def build_digest_use_case(session: AsyncSession) -> NewsDigestInteractor | None:
    """NEWS_DIGEST_* 세 값이 다 있어야 메일을 켠다 — 없으면 머지해도 아무 일도 없다."""
    to = os.getenv("NEWS_DIGEST_TO", "").strip()
    user = os.getenv("NEWS_DIGEST_SMTP_USER", "").strip()
    password = os.getenv("NEWS_DIGEST_SMTP_PASSWORD", "").strip()
    if not (to and user and password):
        return None
    client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_timeout=1.0,
        socket_connect_timeout=1.0,
    )
    return NewsDigestInteractor(
        repository=NewsPgRepository(session=session),
        classifier=OllamaArticleClassifier(),
        mailer=SmtpDigestMailer(user=user, password=password, to=to),
        ledger=RedisDigestLedger(client),
    )


async def run_digest_once() -> DigestReport | None:
    """스케줄러용 — 시각이 됐고 오늘 안 보냈으면 보낸다. 설정이 없으면 None."""
    factory = get_session_factory()
    async with factory() as session:
        use_case = build_digest_use_case(session)
        return None if use_case is None else await use_case.send_if_due(datetime.now(UTC))


def build_summarize_use_case(session: AsyncSession) -> NewsSummarizeUseCase:
    return NewsSummarizeInteractor(
        repository=NewsPgRepository(session=session), summarizer=OllamaKoSummarizer()
    )


async def run_summarize_once(limit: int) -> SummaryReport:
    """스케줄러용 — 수집 뒤에 이어서 한국어 제목·요약을 limit 건까지."""
    factory = get_session_factory()
    async with factory() as session:
        return await build_summarize_use_case(session).summarize_pending(limit)
