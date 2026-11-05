"""RSS·Atom 어댑터 — 섹션별 '최신' 목록.

피드가 준 것(제목·요약·링크·날짜·작성자, 일부는 content 본문)만 쓴다. 기사 원문 페이지는
가져오지 않는다(저장소 저작권 원칙). 피드 목록은 latest_feeds.json — 2026-11-05 응답 확인:
AI 섹션 22곳(연구소 블로그·논문·릴리스·해설·커뮤니티·국내 AI 매체) + 경제 섹션 14곳.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from news.app.dtos.news_dtos import FeedSource, FetchedArticle
from news.app.ports.output.news_source_ports import FeedReaderPort
from news.domain.sections import GROUPS
from news.domain.url import domain_of_url

USER_AGENT = "suvisdev-news/0.1 (+https://news.suvisdev.cloud)"
_FEEDS_PATH = Path(__file__).resolve().parent / "latest_feeds.json"
# arXiv RSS 요약 머리말. 개정 공지(replace·replace-cross)는 새 논문이 아니라 건너뛴다 —
# 11-05 cs.CL 159건 중 69건, cs.LG 445건 중 193건이 개정이었다.
_ARXIV_HEAD = re.compile(r"^arXiv:\S+\s+Announce Type:\s*(\S+)\s+Abstract:\s*", re.IGNORECASE)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@lru_cache(maxsize=1)
def load_latest_feeds() -> tuple[FeedSource, ...]:
    raw: list[dict[str, Any]] = json.loads(_FEEDS_PATH.read_text(encoding="utf-8"))
    feeds: list[FeedSource] = []
    for f in raw:
        group = str(f["group"])
        if group not in GROUPS or group == "search":  # search 는 검색 API 결과 전용 묶음
            raise ValueError(f"latest_feeds.json: {f['name']} 의 group {group!r} 이 잘못됨")
        feeds.append(
            FeedSource(
                name=str(f["name"]),
                url=str(f["url"]),
                group=group,
                max_items=int(f.get("max_items", 50)),
            )
        )
    return tuple(feeds)


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
    """피드 → 기사. 최신 feed.max_items 건만 돌려준다(날짜 없는 글은 뒤로)."""
    parsed = feedparser.parse(content)
    out: list[FetchedArticle] = []
    for entry in parsed.entries:
        url = str(entry.get("link") or "").strip()
        title = _text(str(entry.get("title") or ""))
        if not url or not title:
            continue
        summary = _text(str(entry.get("summary") or ""))
        head = _ARXIV_HEAD.match(summary)
        if head:
            if head.group(1).lower().startswith("replace"):
                continue
            summary = summary[head.end() :]
        body = ""
        contents = entry.get("content") or []
        if contents:
            body = _text(str(contents[0].get("value") or ""))
        if body and (body == summary or not summary):
            summary = body[:500]  # 릴리스 노트처럼 요약 없이 본문만 주는 피드
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
                section=feed.section,
                group=feed.group,
            )
        )
    out.sort(key=lambda a: a.published_at or _EPOCH, reverse=True)
    return out[: feed.max_items]


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
