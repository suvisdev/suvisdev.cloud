"""언론사 RSS 어댑터 — '최신 뉴스' 탭.

피드가 준 것(제목·요약·링크·날짜·작성자, 일부 매체는 content:encoded 본문)만 쓴다. 기사 원문 페이지는
가져오지 않는다(저장소 저작권 원칙). 피드 목록은 latest_feeds.json — 2026-11-05 에 13곳 응답 확인.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from news.app.dtos.news_dtos import FeedSource, FetchedArticle
from news.app.ports.output.news_source_ports import FeedReaderPort
from news.domain.url import domain_of_url

USER_AGENT = "suvisdev-news/0.1 (+https://news.suvisdev.cloud)"
_FEEDS_PATH = Path(__file__).resolve().parent / "latest_feeds.json"


@lru_cache(maxsize=1)
def load_latest_feeds() -> tuple[FeedSource, ...]:
    raw: list[dict[str, str]] = json.loads(_FEEDS_PATH.read_text(encoding="utf-8"))
    return tuple(FeedSource(name=f["name"], url=f["url"]) for f in raw)


def _text(html_or_text: str) -> str:
    if "<" not in html_or_text:
        return " ".join(html_or_text.split())
    return BeautifulSoup(html_or_text, "html.parser").get_text(separator="\n", strip=True)


def _published(entry: Any) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(parsed[0], parsed[1], parsed[2], parsed[3], parsed[4], parsed[5], tzinfo=UTC)


def parse_feed(content: bytes | str, feed: FeedSource) -> list[FetchedArticle]:
    parsed = feedparser.parse(content)
    out: list[FetchedArticle] = []
    for entry in parsed.entries:
        url = str(entry.get("link") or "").strip()
        title = _text(str(entry.get("title") or ""))
        if not url or not title:
            continue
        summary = _text(str(entry.get("summary") or ""))
        body = ""
        contents = entry.get("content") or []
        if contents:
            body = _text(str(contents[0].get("value") or ""))
        if body and body == summary:
            summary = body[:300]
        out.append(
            FetchedArticle(
                url=url,
                title=title,
                summary=summary[:1000],
                source_domain=domain_of_url(url),
                origin="feed",
                published_at=_published(entry),
                source_name=feed.name,
                body=body,
                author=str(entry.get("author") or "").strip(),
            )
        )
    return out


class RssFeedReader(FeedReaderPort):
    def __init__(
        self, timeout: float = 15.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._timeout = timeout
        self._transport = transport

    async def read(self, feed: FeedSource) -> list[FetchedArticle]:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            res = await client.get(feed.url)
            res.raise_for_status()
        return parse_feed(res.content, feed)
