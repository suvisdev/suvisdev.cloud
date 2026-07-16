"""crawl-batch(CrawlScheduleInteractor) 전용 VO — 전부 불변(frozen dataclass)이다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlPolicy:
    """crawl_config.yaml 한 항목 — 사이트 하나에 대한 재수집 정책.

    keywords(정적)와 keyword_source(동적, KEYWORD_SOURCE_REGISTRY 참조) 중 최소 하나는
    있어야 한다 — 배치 시점에 CrawlScheduleInteractor가 keyword_source를 resolve()해서
    keywords와 합친다.
    """

    site_id: str
    keywords: tuple[str, ...]
    interval_minutes: int
    limit_per_keyword: int | None = None  # None이면 CrawlScheduleInteractor 기본값을 쓴다
    keyword_source: str | None = None  # KEYWORD_SOURCE_REGISTRY의 source_id

    def __post_init__(self) -> None:
        if not self.site_id.strip():
            raise ValueError("사이트 ID는 공백일 수 없습니다.")
        if not self.keywords and not self.keyword_source:
            raise ValueError("keywords 또는 keyword_source 중 하나는 있어야 합니다.")
        if self.interval_minutes <= 0:
            raise ValueError("interval_minutes는 양수여야 합니다.")
        if self.limit_per_keyword is not None and self.limit_per_keyword <= 0:
            raise ValueError("limit_per_keyword는 양수여야 합니다.")
