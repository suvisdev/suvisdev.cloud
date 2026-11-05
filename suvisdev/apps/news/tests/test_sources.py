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


_ARXIV = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>cs.CL updates on arXiv.org</title>
<item><title>Sparse Experts</title><link>https://arxiv.org/abs/2611.00001</link>
<description>arXiv:2611.00001v1 Announce Type: new
Abstract: We study sparse experts.</description>
<pubDate>Thu, 05 Nov 2026 00:00:00 -0500</pubDate></item>
<item><title>Old Paper v3</title><link>https://arxiv.org/abs/2401.00002</link>
<description>arXiv:2401.00002v3 Announce Type: replace
Abstract: Revised.</description>
<pubDate>Thu, 05 Nov 2026 00:00:00 -0500</pubDate></item>
<item><title>Cross Paper</title><link>https://arxiv.org/abs/2611.00003</link>
<description>arXiv:2611.00003v1 Announce Type: replace-cross
Abstract: Revised cross.</description>
<pubDate>Thu, 05 Nov 2026 00:00:00 -0500</pubDate></item>
</channel></rss>"""

_ATOM_RELEASES = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Release notes from ollama</title>
<entry><title>v0.13.0</title><link rel="alternate" href="https://github.com/ollama/ollama/releases/tag/v0.13.0"/>
<updated>2026-11-05T01:31:38Z</updated>
<content type="html">&lt;p&gt;New models: example-moe&lt;/p&gt;</content></entry>
<entry><title>v0.12.9</title><link rel="alternate" href="https://github.com/ollama/ollama/releases/tag/v0.12.9"/>
<updated>2026-10-30T01:00:00Z</updated>
<content type="html">&lt;p&gt;Fixes&lt;/p&gt;</content></entry>
</feed>"""


def test_parse_feed_reads_content_and_author():
    feed = FeedSource(name="가나일보", url="https://x.example/rss", group="outlet")
    (a,) = parse_feed(_RSS.encode(), feed)
    assert a.title == "시립도서관 야간 운영 늘린다"
    assert a.summary == "가나시 시립도서관이 밤 10시까지 연다."
    assert "시는 3일 발표했다." in a.body  # content:encoded 본문
    assert a.author == "김민준 기자" and a.source_name == "가나일보" and a.origin == "feed"
    assert a.section == "economy" and a.group == "outlet"


def test_parse_feed_unescapes_double_encoded_title():
    rss = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>x</title><item>'
        "<title>&amp;quot;페트병&amp;quot; 위장…&amp;#039;과징금&amp;#039; 유지</title>"
        "<link>https://x.example/1</link><pubDate>Thu, 05 Nov 2026 08:58:00 +0900</pubDate>"
        "</item></channel></rss>"
    )
    feed = FeedSource(name="머니투데이", url="https://x.example/rss", group="outlet")
    (a,) = parse_feed(rss.encode(), feed)
    assert a.title == "\"페트병\" 위장…'과징금' 유지"


def test_parse_feed_skips_arxiv_revisions_and_strips_header():
    feed = FeedSource(name="arXiv", url="https://rss.arxiv.org/rss/cs.CL", group="paper")
    (a,) = parse_feed(_ARXIV.encode(), feed)
    assert a.title == "Sparse Experts" and a.summary == "We study sparse experts."
    assert a.section == "ai" and a.group == "paper"


def test_parse_feed_keeps_newest_n_and_uses_body_when_no_summary():
    feed = FeedSource(name="Ollama", url="https://g.example/r.atom", group="release", max_items=1)
    (a,) = parse_feed(_ATOM_RELEASES.encode(), feed)
    assert a.title == "v0.13.0"  # 최신 1건만
    assert a.summary == "New models: example-moe"


@pytest.mark.asyncio
async def test_rss_reader_fetches_with_user_agent():
    agents: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        agents.append(req.headers["user-agent"])
        return httpx.Response(200, content=_RSS.encode())

    reader = RssFeedReader(transport=httpx.MockTransport(handler))
    items = await reader.read(
        FeedSource(name="가나일보", url="https://x.example/rss", group="outlet")
    )
    assert len(items) == 1 and agents[0].startswith("suvisdev-news/")


def test_latest_feed_list_is_valid():
    feeds = load_latest_feeds()
    assert len({f.url for f in feeds}) == len(feeds)
    by_section = {s: [f for f in feeds if f.section == s] for s in ("ai", "economy")}
    assert len(by_section["ai"]) >= 15 and len(by_section["economy"]) >= 10  # AI 가 메인
    assert all(f.group != "search" for f in feeds)
    assert not any("sbs.co.kr" in f.url for f in feeds)  # SBS RSS 는 개인 리더 이용만 허용
