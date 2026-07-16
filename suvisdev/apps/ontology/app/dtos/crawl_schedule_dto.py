"""crawl-batch(CrawlScheduleInteractor) 전용 VO — 전부 불변(frozen dataclass)이다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlPolicy:
    """crawl_config.yaml 한 항목 — 사이트 하나에 대한 재수집 정책."""

    site_id: str
    keywords: tuple[str, ...]
    interval_minutes: int
    limit_per_keyword: int | None = None  # None이면 CrawlScheduleInteractor 기본값을 쓴다

    def __post_init__(self) -> None:
        if not self.site_id.strip():
            raise ValueError("사이트 ID는 공백일 수 없습니다.")
        if not self.keywords:
            raise ValueError("keywords는 최소 1개 이상이어야 합니다.")
        if self.interval_minutes <= 0:
            raise ValueError("interval_minutes는 양수여야 합니다.")
        if self.limit_per_keyword is not None and self.limit_per_keyword <= 0:
            raise ValueError("limit_per_keyword는 양수여야 합니다.")
