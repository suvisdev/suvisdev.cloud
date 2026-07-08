"""KOFIC 박스오피스 import DTO·Command."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoxOfficeEntryDto:
    """KOFIC 박스오피스 한 항목 — raw dict를 정규화한 것."""

    rank: int
    movie_cd: str
    title: str


@dataclass(frozen=True)
class KoficImportCommand:
    """KOFIC 주간 박스오피스 수입 — target_date 없으면 어댑터가 전일로 기본."""

    target_date: str | None = None
    week_gb: str = "0"
