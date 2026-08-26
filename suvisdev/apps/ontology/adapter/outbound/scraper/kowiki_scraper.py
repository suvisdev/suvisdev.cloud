"""한국어 위키백과 MediaWiki API 어댑터 — ScrapeDatasetInteractor(온디맨드 CLI)가 쓰는 스크래퍼.

HTML을 직접 긁지 않고 공식 API만 쓴다 (robots 이슈 원천 차단, 파싱 안정성 확보).
검색(action=query) → 문서별 본문(action=parse, wikitext) 2단계. {{영화 정보}} infobox가
없는 문서(인물·서사시 등)는 영화가 아니므로 스킵하고 로그를 남긴다.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import quote

import mwparserfromhell

from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.site_scraper_port import SiteScraperPort

logger = logging.getLogger(__name__)

_SEARCH_URL = (
    "https://ko.wikipedia.org/w/api.php"
    "?action=query&list=search&srsearch={query}&format=json&srlimit={limit}"
)
_PARSE_URL = (
    "https://ko.wikipedia.org/w/api.php?action=parse&page={title}&format=json&prop=wikitext"
)
_RATE_DOMAIN = "ko.wikipedia.org"
_MOVIE_INFOBOX_TEMPLATE = "영화 정보"
_WANTED_SECTIONS = {"줄거리", "평가", "출연", "제작"}
_REF_TAG_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.DOTALL)


def _strip_refs(wikitext: str) -> str:
    return _REF_TAG_RE.sub("", wikitext)


def _plain_text(wikitext: str) -> str:
    return mwparserfromhell.parse(wikitext).strip_code().strip()


def _extract_infobox(code: mwparserfromhell.wikicode.Wikicode) -> dict[str, str] | None:
    for template in code.filter_templates():
        if template.name.strip() != _MOVIE_INFOBOX_TEMPLATE:
            continue
        infobox = {}
        for param in template.params:
            value = param.value.strip_code().strip()
            if value:
                infobox[param.name.strip()] = value
        return infobox or None
    return None


def _extract_sections(code: mwparserfromhell.wikicode.Wikicode) -> tuple[str, dict[str, str]]:
    lead = ""
    sections: dict[str, str] = {}
    for part in code.get_sections(levels=[2], include_lead=True):
        headings = part.filter_headings()
        if not headings:
            lead = _plain_text(str(part))
            continue
        title = headings[0].title.strip()
        body = str(part).replace(str(headings[0]), "", 1)
        text = _plain_text(body)
        if title in _WANTED_SECTIONS and text:
            sections[title] = text
    return lead, sections


def _movie_query(keyword: str) -> str:
    """검색 정밀도를 높이기 위해 "(영화)" 접미사를 붙인다.

    "오디세이"처럼 동음이의 문서가 많은 키워드에서 서사시·인물 대신
    영화 문서를 상위로 올리는 효과가 있다.
    """
    if "(영화)" in keyword:
        return keyword
    return f"{keyword} (영화)"


class KowikiScraper(SiteScraperPort):
    site_id = "kowiki"
    user_agent = "SUVIS-harvester/0.1 (personal project; contact via github)"

    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        query = _movie_query(keyword)
        self._rate_limiter.acquire(_RATE_DOMAIN)
        search_url = _SEARCH_URL.format(query=quote(query), limit=limit)
        search_payload = json.loads(self._fetcher.fetch(search_url))
        titles = [item["title"] for item in search_payload.get("query", {}).get("search", [])]

        for title in titles[:limit]:
            url = f"https://ko.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
            self._rate_limiter.acquire(_RATE_DOMAIN)
            if self._visited_store.is_visited(keyword, url):
                continue
            self._visited_store.mark(keyword, url)

            parse_url = _PARSE_URL.format(title=quote(title))
            parse_payload = json.loads(self._fetcher.fetch(parse_url))
            wikitext = _strip_refs(parse_payload["parse"]["wikitext"]["*"])
            code = mwparserfromhell.parse(wikitext)

            infobox = _extract_infobox(code)
            if infobox is None:
                logger.info(
                    "[KowikiScraper] 영화 infobox 없음, 스킵 | keyword=%s title=%s",
                    keyword,
                    title,
                )
                continue

            lead, sections = _extract_sections(code)

            yield ScrapedRecord(
                source=self.site_id,
                keyword=keyword,
                url=url,
                title=title,
                content=lead,
                author_hash=hashlib.sha256(title.encode()).hexdigest()[:8],
                scraped_at=datetime.now(UTC),
                sections=sections or None,
                infobox=infobox,
            )
