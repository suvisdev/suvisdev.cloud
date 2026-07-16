"""httpx 기반 PageFetcherPort 구현체(동기) — 사이트 어댑터가 공용으로 쓴다.

harvester CLI는 배치성 스크립트라 async 이벤트 루프가 필요 없다 — 여기만 동기로 간다
(ontology의 FastAPI 라우터 쪽 어댑터들과는 다른 이유다).
"""

from __future__ import annotations

import httpx

from ontology.app.ports.output.crawl_errors import CrawlFetchError
from ontology.app.ports.output.page_fetcher_port import PageFetcherPort

_DEFAULT_USER_AGENT = "SuvisdevOntologyHarvester/1.0"


class HttpxPageFetcherAdapter(PageFetcherPort):
    def __init__(self, *, timeout: float = 15.0, user_agent: str = _DEFAULT_USER_AGENT) -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    def fetch(self, url: str) -> str:
        try:
            with httpx.Client(
                timeout=self._timeout,
                headers={"User-Agent": self._user_agent},
                follow_redirects=True,
            ) as client:
                r = client.get(url)
        except httpx.TimeoutException as e:
            raise CrawlFetchError(f"응답 타임아웃: {url}", status_code=504) from e
        except httpx.TransportError as e:
            raise CrawlFetchError(f"연결 실패: {url} ({e!s})", status_code=503) from e

        if r.status_code != 200:
            raise CrawlFetchError(f"HTTP {r.status_code}: {url}", status_code=r.status_code)
        return r.text
