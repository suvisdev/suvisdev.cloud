"""RSS·Atom 어댑터 — 섹션별 '최신' 목록.

피드가 준 것(제목·요약·링크·날짜·작성자, 일부는 content 본문)만 쓴다. 기사 원문 페이지는
가져오지 않는다(저장소 저작권 원칙). 피드 목록은 latest_feeds.json — 2026-11-05 응답 확인:
AI 섹션 22곳(연구소 블로그·논문·릴리스·해설·커뮤니티·국내 AI 매체) + 경제 섹션 13곳
(한겨레 경제는 글에 날짜가 없어 뺐다).
"""

from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime, timedelta
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
# 날짜 문자열 끝에 시간대(Z, +09:00, +0900, GMT, KST …)가 있는가. 없으면 feedparser 가 UTC 로 읽는다 —
# 11-05 운영 첫 수집에서 한국 시각을 UTC 로 읽어 국내 AI 매체 글이 9시간 미래로 저장돼 AI 메인 맨 위를 차지했다.
_HAS_TZ = re.compile(r"(?:Z|[+-]\d{2}:?\d{2}|[A-Za-z]{2,5})\s*$")
_TZ_SETTING = re.compile(r"^([+-])(\d{2}):(\d{2})$")


def _tz_minutes(setting: str) -> int:
    m = _TZ_SETTING.match(setting)
    if not m:
        raise ValueError(f"latest_feeds.json: naive_tz {setting!r} 는 +09:00 꼴이어야 함")
    minutes = int(m.group(2)) * 60 + int(m.group(3))
    return -minutes if m.group(1) == "-" else minutes


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
                naive_tz_minutes=_tz_minutes(str(f.get("naive_tz", "+00:00"))),
            )
        )
    return tuple(feeds)


def _text(html_or_text: str) -> str:
    # 제목에 개체가 두 번 인코딩된 피드가 있다(머니투데이 `&amp;quot;` → 한 번 풀면 `&quot;` 가 화면에 남음, 11-05).
    # feedparser·BeautifulSoup 가 한 번 푼 뒤 남은 개체를 한 번 더 푼다.
    if "<" not in html_or_text:
        return html.unescape(" ".join(html_or_text.split()))
    text = BeautifulSoup(html_or_text, "html.parser").get_text(separator="\n", strip=True)
    return html.unescape(text)


def _published(entry: Any, naive_tz_minutes: int = 0) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    dt = datetime(parsed[0], parsed[1], parsed[2], parsed[3], parsed[4], parsed[5], tzinfo=UTC)
    raw = str(entry.get("published") or entry.get("updated") or "").strip()
    if naive_tz_minutes and raw and not _HAS_TZ.search(raw):
        dt -= timedelta(minutes=naive_tz_minutes)  # 현지 시각으로 적힌 값을 UTC 로
    return dt


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
                published_at=_published(entry, feed.naive_tz_minutes),
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
