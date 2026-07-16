"""KOBIS 어제 박스오피스 top10 제목 — KeywordSourcePort 구현체.

kobis_scraper.py와 API 호출 로직(kobis_client)을 공유한다 — 여기서 새로 HTTP 코드를
쓰지 않는다. 제목은 원제 그대로 반환한다(괄호 부제 제거 등 정규화는 안 함 — 뉴스/위키
검색 재현율은 후처리 책임).
"""

from __future__ import annotations

from ontology.adapter.outbound.config.api_keys import get_kobis_api_key
from ontology.adapter.outbound.scraper.kobis_client import fetch_daily_boxoffice, yesterday_kst
from ontology.app.ports.output.keyword_source_port import KeywordSourcePort
from ontology.app.ports.output.page_fetcher_port import PageFetcherPort
from ontology.app.ports.output.rate_limiter_port import RateLimiterPort

_RATE_DOMAIN = "kobis.or.kr"
_TOP_N = 10


class KobisBoxofficeTitleSource(KeywordSourcePort):
    source_id = "kobis_boxoffice_titles"

    def __init__(self, *, fetcher: PageFetcherPort, rate_limiter: RateLimiterPort) -> None:
        self._fetcher = fetcher
        self._rate_limiter = rate_limiter

    def resolve(self) -> list[str]:
        api_key = get_kobis_api_key()
        target_dt = yesterday_kst()

        self._rate_limiter.acquire(_RATE_DOMAIN)
        items = fetch_daily_boxoffice(self._fetcher, api_key=api_key, target_dt=target_dt)

        titles = [str(item.get("movieNm", "")) for item in items[:_TOP_N]]
        return [t for t in titles if t]
