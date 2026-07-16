"""harvester JSONL → mova RAG 적재 유스케이스 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HarvestRow:
    """harvester JSONL 한 줄. harvester의 ScrapedRecord와는 별도 타입이다 —
    mova는 harvester 모듈을 import하지 않고 JSONL 파일 포맷만을 계약으로 삼는다.
    """

    source: str
    url: str
    title: str
    content: str
    sections: dict[str, str] | None = None
    infobox: dict[str, str] | None = None
    external_ids: dict[str, str] | None = None
    metrics: dict[str, float] | None = None


@dataclass(frozen=True)
class HarvestIngestResultDto:
    """ingest-harvest 실행 1회 요약."""

    total: int
    ingested: int
    matched: int
    unmatched: int
