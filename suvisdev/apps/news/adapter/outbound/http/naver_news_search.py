"""네이버 뉴스 검색 API 어댑터.

입구가 두 가지다 — 개발자센터(openapi.naver.com)와 NAVER API HUB(naverapihub.apigw.ntruss.com).
요청 파라미터·응답 형식·하루 25,000회 한도는 같고 주소와 인증 헤더 이름만 다르다.
NAVER_SEARCH_API_URL 의 호스트로 헤더 이름을 고른다. 응답에는 본문이 없다(제목·요약·링크·날짜만).
"""

from __future__ import annotations

import html
import os
import re
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from news.app.dtos.news_dtos import FetchedArticle
from news.app.ports.output.news_source_ports import NewsSearchPort
from news.domain.url import domain_of_url

DEFAULT_API_URL = "https://openapi.naver.com/v1/search/news.json"
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return " ".join(html.unescape(_TAG.sub("", text or "")).split())


def parse_naver_items(data: dict[str, Any]) -> list[FetchedArticle]:
    out: list[FetchedArticle] = []
    for item in data.get("items", []):
        original = str(item.get("originallink") or "").strip()
        link = str(item.get("link") or "").strip()
        url = original or link
        if not url:
            continue
        published = None
        if item.get("pubDate"):
            try:
                published = parsedate_to_datetime(str(item["pubDate"]))
            except (TypeError, ValueError):
                published = None
        out.append(
            FetchedArticle(
                url=url,
                title=_clean(str(item.get("title", ""))),
                summary=_clean(str(item.get("description", ""))),
                source_domain=domain_of_url(url),
                origin="search",
                published_at=published,
                link=link if link and link != url else None,
            )
        )
    return out


class NaverNewsSearchClient(NewsSearchPort):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_url: str = DEFAULT_API_URL,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._id = client_id
        self._secret = client_secret
        self._url = api_url
        self._timeout = timeout
        self._transport = transport

    @classmethod
    def from_env(cls) -> NaverNewsSearchClient:
        return cls(
            client_id=os.getenv("NAVER_SEARCH_CLIENT_ID", "").strip(),
            client_secret=os.getenv("NAVER_SEARCH_CLIENT_SECRET", "").strip(),
            api_url=os.getenv("NAVER_SEARCH_API_URL", "").strip() or DEFAULT_API_URL,
        )

    @property
    def enabled(self) -> bool:
        return bool(self._id and self._secret)

    def _headers(self) -> dict[str, str]:
        if "apigw.ntruss.com" in self._url:
            return {"X-NCP-APIGW-API-KEY-ID": self._id, "X-NCP-APIGW-API-KEY": self._secret}
        return {"X-Naver-Client-Id": self._id, "X-Naver-Client-Secret": self._secret}

    async def search(self, query: str, display: int = 100) -> list[FetchedArticle]:
        params: dict[str, str | int] = {
            "query": query,
            "display": max(1, min(display, 100)),
            "start": 1,
            "sort": "date",
        }
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            res = await client.get(self._url, params=params, headers=self._headers())
            res.raise_for_status()
            data: dict[str, Any] = res.json()
        return parse_naver_items(data)
