"""TMDB(The Movie Database) 어댑터 — ScrapeDatasetInteractor(온디맨드 CLI)가 쓴다.

mova가 이미 쓰는 apps/mova/adapter/outbound/http/tmdb_adapter.py·tmdb_mapper.py의
URL·필드 컨벤션(release_date/overview/genres/genre_ids/credits.cast)을 그대로 따르되,
그쪽은 비동기 httpx라 harvester의 동기 PageFetcherPort 계약에 맞게 새로 짰다(로직만
이식, 코드 재사용은 아님). 감독 추출(credits.crew에서 job=="Director")은 mova
매퍼에 없던 부분이라 여기서 새로 추가했다 — infobox에 "감독"이 필요해서.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from ontology.adapter.outbound.config.api_keys import get_tmdb_api_key
from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.site_scraper_port import SiteScraperPort

_SEARCH_URL = "https://api.themoviedb.org/3/search/movie?query={query}&language=ko-KR&api_key={key}"
_DETAIL_URL = (
    "https://api.themoviedb.org/3/movie/{id}"
    "?language=ko-KR&append_to_response=credits&api_key={key}"
)
_CAST_LIMIT = 5


def _map_cast_names(credits: dict[str, Any], *, limit: int = _CAST_LIMIT) -> list[str]:
    names = []
    for member in credits.get("cast") or []:
        name = str(member.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def _map_directors(credits: dict[str, Any]) -> list[str]:
    names = []
    for member in credits.get("crew") or []:
        if member.get("job") != "Director":
            continue
        name = str(member.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


class TmdbScraper(SiteScraperPort):
    site_id = "tmdb"

    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        api_key = get_tmdb_api_key()

        self._rate_limiter.acquire("api.themoviedb.org")
        search_url = _SEARCH_URL.format(query=quote(keyword), key=api_key)
        results = json.loads(self._fetcher.fetch(search_url)).get("results") or []

        yielded = 0
        for item in results:
            if yielded >= limit:
                break
            tmdb_id = item.get("id")
            if tmdb_id is None:
                continue
            url = f"https://www.themoviedb.org/movie/{tmdb_id}"
            if self._visited_store.is_visited(keyword, url):
                continue
            self._visited_store.mark(keyword, url)

            self._rate_limiter.acquire("api.themoviedb.org")
            detail_url = _DETAIL_URL.format(id=tmdb_id, key=api_key)
            detail = json.loads(self._fetcher.fetch(detail_url))

            credits = detail.get("credits") or {}
            genres = [g.get("name", "") for g in detail.get("genres") or [] if g.get("name")]
            directors = _map_directors(credits)
            cast = _map_cast_names(credits)

            infobox = {}
            if directors:
                infobox["감독"] = ", ".join(directors)
            if cast:
                infobox["출연"] = ", ".join(cast)
            if genres:
                infobox["장르"] = ", ".join(genres)
            if detail.get("release_date"):
                infobox["개봉일"] = str(detail["release_date"])

            title = str(detail.get("title") or item.get("title") or "")

            yield ScrapedRecord(
                source=self.site_id,
                keyword=keyword,
                url=url,
                title=title,
                content=str(detail.get("overview") or "").strip(),
                author_hash=hashlib.sha256(str(tmdb_id).encode()).hexdigest()[:8],
                scraped_at=datetime.now(UTC),
                external_ids={"tmdb_id": str(tmdb_id)},
                infobox=infobox or None,
            )
            yielded += 1
