"""사이트별 스크래퍼 등록 레지스트리 — OCP: 새 사이트는 이 파일 하단에 두 줄만 추가한다.

사이트 어댑터가 이 모듈을 import하게(데코레이터 패턴) 만들면 registry ↔ 어댑터 순환
import가 생긴다(어댑터를 직접 import하는 진입점에서 재현됨) — 그래서 등록은 반대 방향으로,
이 파일이 각 어댑터를 import해서 SITE_REGISTRY에 채워 넣는 방식으로 한다.
"""

from __future__ import annotations

from ontology.app.ports.output.site_scraper_port import SiteScraperPort

SITE_REGISTRY: dict[str, type[SiteScraperPort]] = {}

from ontology.adapter.outbound.scraper.google_news_scraper import GoogleNewsScraper  # noqa: E402
from ontology.adapter.outbound.scraper.kowiki_scraper import KowikiScraper  # noqa: E402

SITE_REGISTRY[GoogleNewsScraper.site_id] = GoogleNewsScraper
SITE_REGISTRY[KowikiScraper.site_id] = KowikiScraper
