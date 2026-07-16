"""동적 키워드 공급원 레지스트리 — SITE_REGISTRY와 동일한 이유로 반대 방향 등록을 쓴다
(registry.py의 순환 임포트 노트 참고)."""

from __future__ import annotations

from ontology.app.ports.output.keyword_source_port import KeywordSourcePort

KEYWORD_SOURCE_REGISTRY: dict[str, type[KeywordSourcePort]] = {}

from ontology.adapter.outbound.scraper.kobis_boxoffice_title_source import (  # noqa: E402
    KobisBoxofficeTitleSource,
)

KEYWORD_SOURCE_REGISTRY[KobisBoxofficeTitleSource.source_id] = KobisBoxofficeTitleSource
