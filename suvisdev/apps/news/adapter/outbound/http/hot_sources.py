"""화제 출처 어댑터 — 사람들의 반응 수치를 준다 (2026-11-06, 키 필요 없음).

- Hugging Face Daily Papers: 그날 올라온 논문과 추천 수. 11-05 39편 중 1위 추천 83
- Hacker News(Algolia 검색 API): 최근 48시간 글의 점수·댓글. AI 글만 제목으로 거른다(domain/hot.py)
원문 페이지는 가져오지 않는다. 논문은 초록, HN 은 작성자가 직접 쓴 글(Ask HN 등)이 있을 때만 요약 내용이 된다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from bs4 import BeautifulSoup

from news.adapter.outbound.http.rss_feed_reader import USER_AGENT
from news.app.dtos.news_dtos import FetchedArticle, HotItem
from news.app.ports.output.news_source_ports import HotSourcePort
from news.domain.hot import (
    HOT_COMMUNITY,
    HOT_PAPERS,
    community_label,
    is_ai_title,
    papers_label,
)
from news.domain.url import domain_of_url

HF_URL = "https://huggingface.co/api/daily_papers"
HN_URL = "https://hn.algolia.com/api/v1/search"
MAX_ITEMS = 30
HN_MIN_POINTS = 100
HN_WINDOW_HOURS = 48


def _iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_hf_papers(rows: list[dict[str, Any]]) -> list[HotItem]:
    items: dict[str, HotItem] = {}
    for row in rows:
        paper = row.get("paper") or {}
        paper_id = str(paper.get("id") or "").strip()
        title = " ".join(str(paper.get("title") or row.get("title") or "").split())
        if not paper_id or not title:
            continue
        upvotes = int(paper.get("upvotes") or 0)
        url = f"https://arxiv.org/abs/{paper_id}"
        items[url] = HotItem(
            article=FetchedArticle(
                url=url,
                title=title,
                summary=" ".join(str(paper.get("summary") or "").split())[:1000],
                source_domain="arxiv.org",
                origin="feed",
                published_at=_iso(row.get("publishedAt") or paper.get("publishedAt")),
                source_name="HF 화제 논문",
                section="ai",
                group="paper",
            ),
            source=HOT_PAPERS,
            score=upvotes,
            label=papers_label(upvotes),
        )
    return sorted(items.values(), key=lambda i: -i.score)[:MAX_ITEMS]


def parse_hn_hits(hits: list[dict[str, Any]]) -> list[HotItem]:
    out: list[HotItem] = []
    for hit in hits:
        title = " ".join(str(hit.get("title") or "").split())
        object_id = str(hit.get("objectID") or "")
        if not title or not object_id or not is_ai_title(title):
            continue
        url = str(hit.get("url") or "") or f"https://news.ycombinator.com/item?id={object_id}"
        created = hit.get("created_at_i")
        story = str(hit.get("story_text") or "")
        points = int(hit.get("points") or 0)
        out.append(
            HotItem(
                article=FetchedArticle(
                    url=url,
                    title=title,
                    summary=BeautifulSoup(story, "html.parser").get_text(" ", strip=True)[:1000]
                    if story
                    else "",
                    source_domain=domain_of_url(url),
                    origin="feed",
                    published_at=datetime.fromtimestamp(created, UTC)
                    if isinstance(created, int)
                    else None,
                    source_name="Hacker News",
                    section="ai",
                    group="community",
                ),
                source=HOT_COMMUNITY,
                score=points,
                label=community_label(points, int(hit.get("num_comments") or 0)),
            )
        )
    return sorted(out, key=lambda i: -i.score)[:MAX_ITEMS]


class _JsonSource(HotSourcePort):
    def __init__(
        self, timeout: float = 20.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._timeout = timeout
        self._transport = transport

    async def _get(self, url: str, params: dict[str, str | int]) -> Any:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            res = await client.get(url, params=params)
            res.raise_for_status()
        return res.json()


class HuggingFacePapersSource(_JsonSource):
    @property
    def name(self) -> str:
        return HOT_PAPERS

    async def fetch(self) -> list[HotItem]:
        # 오늘 것은 아직 추천이 적으니 어제 것까지 함께 본다
        today = datetime.now(UTC).date()
        rows: list[dict[str, Any]] = []
        for day in (today, today - timedelta(days=1)):
            data = await self._get(HF_URL, {"date": day.isoformat(), "limit": 100})
            if isinstance(data, list):
                rows.extend(data)
        return parse_hf_papers(rows)


class HackerNewsSource(_JsonSource):
    @property
    def name(self) -> str:
        return HOT_COMMUNITY

    async def fetch(self) -> list[HotItem]:
        since = int((datetime.now(UTC) - timedelta(hours=HN_WINDOW_HOURS)).timestamp())
        data = await self._get(
            HN_URL,
            {
                "tags": "story",
                "numericFilters": f"points>{HN_MIN_POINTS},created_at_i>{since}",
                "hitsPerPage": 200,
            },
        )
        hits = data.get("hits") if isinstance(data, dict) else None
        return parse_hn_hits(hits if isinstance(hits, list) else [])
