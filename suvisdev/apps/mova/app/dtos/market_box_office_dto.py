"""KOFIC 박스오피스 import DTO·Command."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoxOfficeEntryDto:
    """KOFIC 박스오피스 한 항목 — raw dict를 정규화한 것."""

    rank: int
    movie_cd: str
    title: str
    # 개봉 연도(KOFIC openDt) — 같은 제목이 여러 편일 때(인턴 2015/2026) 상영 중인 쪽을 고르는 근거.
    open_year: int | None = None


@dataclass(frozen=True)
class KoficImportCommand:
    """KOFIC 주간 박스오피스 수입 — target_date 없으면 어댑터가 전일로 기본."""

    target_date: str | None = None
    week_gb: str = "0"
