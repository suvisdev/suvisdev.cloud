"""Hub 지식 저장소(hub_knowledge) DTO — Spoke는 이 순수 dto만 채워 Hub에 넘긴다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HubKnowledgeUpsertCommand:
    """Spoke → Hub ingest 요청. Hub는 Spoke의 ORM·스키마를 모른다."""

    source: str
    source_ref: str
    title: str
    content: str


@dataclass(frozen=True)
class HubKnowledgeHitDto:
    """벡터 검색 결과 1건."""

    source_ref: str
    title: str
    content: str
    score: float
