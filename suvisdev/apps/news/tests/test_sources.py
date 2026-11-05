"""검색 API·RSS 어댑터 — 실제 네트워크 없이 httpx MockTransport 와 고정 XML 로."""

import httpx
import pytest

from news.adapter.outbound.http.naver_news_search import NaverNewsSearchClient, parse_naver_items
from news.adapter.outbound.http.rss_feed_reader import RssFeedReader, load_latest_feeds, parse_feed
from news.app.dtos.news_dtos import FeedSource

_NAVER = {
    "items": [
        {
            "title": "<b>반도체</b> 수출 &quot;역대 최대&quot;",
            "originallink": "https://www.ganadaily.example/news/1?utm_source=naver",
            "link": "https://n.news.naver.com/mnews/article/001/0000000001",
            "description": "올해 <b>반도체</b> 수출이 늘었다.",
            "pubDate": "Wed, 05 Nov 2026 09:30:00 +0900",
        },
        {"title": "링크 없음", "originallink": "", "link": "", "description": "", "pubDate": ""},
    ]
}

_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>가나일보</title>
<item>
  <title>시립도서관 야간 운영 늘린다</title>
  <link>https://www.ganadaily.example/news/0001</link>
  <description><![CDATA[<p>가나시 시립도서관이 밤 10시까지 연다.</p>]]></description>
  <content:encoded><![CDATA[<p>가나시 시립도서관이 다음 달부터 평일 밤 10시까지 연다.</p><p>시는 3일 발표했다.</p>]]></content:encoded>
  <dc:creator>김민준 기자</dc:creator>
  <pubDate>Mon, 03 Nov 2026 09:00:00 +0900</pubDate>
</item>
<item><title></title><link>https://www.ganadaily.example/news/0002</link></item>
</channel></rss>"""


def test_parse_naver_items_strips_tags_and_keeps_original_link():
    (a,) = parse_naver_items(_NAVER)
    assert a.title == '반도체 수출 "역대 최대"'
    assert a.summary == "올해 반도체 수출이 늘었다."
    assert a.url.startswith("https://www.ganadaily.example/news/1")
    assert a.link and a.link.startswith("https://n.news.naver.com/")
    assert a.source_domain == "ganadaily.example" and a.origin == "search"
    assert a.published_at is not None and a.published_at.utcoffset() is not None


@pytest.mark.asyncio
async def test_naver_client_header_kind_follows_api_url():
    seen: dict[str, str] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(req.headers)
        seen["query"] = req.url.params["query"]
        return httpx.Response(200, json=_NAVER)

    hub = NaverNewsSearchClient(
        "id",
        "secret",
        api_url="https://naverapihub.apigw.ntruss.com/search/v1/news",
        transport=httpx.MockTransport(handler),
    )
    items = await hub.search("반도체")
    assert len(items) == 1 and seen["query"] == "반도체"
    assert seen["x-ncp-apigw-api-key-id"] == "id"

    seen.clear()
    dev = NaverNewsSearchClient("id", "secret", transport=httpx.MockTransport(handler))
    await dev.search("반도체")
    assert seen["x-naver-client-id"] == "id"


def test_naver_client_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("NAVER_SEARCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_SEARCH_CLIENT_SECRET", raising=False)
    assert NaverNewsSearchClient.from_env().enabled is False


def test_parse_feed_reads_content_and_author():
    (a,) = parse_feed(_RSS.encode(), FeedSource(name="가나일보", url="https://x.example/rss"))
    assert a.title == "시립도서관 야간 운영 늘린다"
    assert a.summary == "가나시 시립도서관이 밤 10시까지 연다."
    assert "시는 3일 발표했다." in a.body  # content:encoded 본문
    assert a.author == "김민준 기자" and a.source_name == "가나일보" and a.origin == "feed"


@pytest.mark.asyncio
async def test_rss_reader_fetches_with_user_agent():
    agents: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        agents.append(req.headers["user-agent"])
        return httpx.Response(200, content=_RSS.encode())

    reader = RssFeedReader(transport=httpx.MockTransport(handler))
    items = await reader.read(FeedSource(name="가나일보", url="https://x.example/rss"))
    assert len(items) == 1 and agents[0].startswith("suvisdev-news/")


def test_latest_feed_list_is_valid():
    feeds = load_latest_feeds()
    assert len(feeds) >= 10
    assert len({f.url for f in feeds}) == len(feeds)
