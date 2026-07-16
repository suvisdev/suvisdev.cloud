"""KOBIS(영화진흥위원회) 일별 박스오피스 어댑터 — CrawlScheduleInteractor(배치)가 쓴다.

keyword는 특수 규약: "daily"(어제 KST 박스오피스) 또는 "daily:YYYYMMDD"(지정 날짜).
dedup 키는 movieCd:targetDt다 — 같은 영화라도 날짜가 다르면 새 레코드(일별 관객
추이 자체가 데이터라서). KOBIS 상세 API는 줄거리를 안 주기 때문에(공식 API 필드에
없음) content는 실제로 있는 필드(감독/장르/관람등급/상영시간)로만 구성한다.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from ontology.adapter.outbound.config.api_keys import get_kobis_api_key
from ontology.adapter.outbound.scraper.kobis_client import (
    fetch_daily_boxoffice,
    fetch_movie_detail,
    yesterday_kst,
)
from ontology.app.dtos.scrape_dto import ScrapedRecord
from ontology.app.ports.output.site_scraper_port import SiteScraperPort

logger = logging.getLogger(__name__)

_RATE_DOMAIN = "kobis.or.kr"


def _parse_target_dt(keyword: str) -> str:
    if ":" in keyword:
        _, explicit = keyword.split(":", 1)
        return explicit
    return yesterday_kst()


def _to_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _build_content(detail: dict[str, Any]) -> str:
    directors = ", ".join(d.get("peopleNm", "") for d in detail.get("directors") or [])
    genres = ", ".join(g.get("genreNm", "") for g in detail.get("genres") or [])
    audits = detail.get("audits") or []
    watch_grade = audits[0].get("watchGradeNm", "") if audits else ""
    show_tm = detail.get("showTm", "")

    parts = []
    if directors:
        parts.append(f"감독: {directors}")
    if genres:
        parts.append(f"장르: {genres}")
    if watch_grade:
        parts.append(f"관람등급: {watch_grade}")
    if show_tm:
        parts.append(f"상영시간: {show_tm}분")
    return "\n".join(parts)


class KobisScraper(SiteScraperPort):
    site_id = "kobis"

    def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
        api_key = get_kobis_api_key()
        target_dt = _parse_target_dt(keyword)

        self._rate_limiter.acquire(_RATE_DOMAIN)
        items = fetch_daily_boxoffice(self._fetcher, api_key=api_key, target_dt=target_dt)

        yielded = 0
        for item in items:
            if yielded >= limit:
                break
            movie_cd = str(item.get("movieCd", ""))
            dedup_key = f"{movie_cd}:{target_dt}"
            if self._visited_store.is_visited(keyword, dedup_key):
                continue
            self._visited_store.mark(keyword, dedup_key)

            self._rate_limiter.acquire(_RATE_DOMAIN)
            detail = fetch_movie_detail(self._fetcher, api_key=api_key, movie_cd=movie_cd)

            url = (
                "https://www.kobis.or.kr/kobis/business/mast/mvie/searchMovieDtl.do"
                f"?movieCd={movie_cd}"
            )
            metrics = {
                "rank": _to_float(item.get("rank")),
                "audi_cnt": _to_float(item.get("audiCnt")),
                "audi_acc": _to_float(item.get("audiAcc")),
            }

            yield ScrapedRecord(
                source=self.site_id,
                keyword=keyword,
                url=url,
                title=str(item.get("movieNm", "")),
                content=_build_content(detail),
                author_hash=hashlib.sha256(movie_cd.encode()).hexdigest()[:8],
                scraped_at=datetime.now(UTC),
                external_ids={"kobis_movie_cd": movie_cd},
                metrics=metrics,
            )
            yielded += 1
