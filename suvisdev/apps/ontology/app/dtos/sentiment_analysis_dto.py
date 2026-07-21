from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentResult:
    """감정 분석 결과 — 극성 라벨·신뢰도·(생성형)근거."""

    label: str
    score: float
    reason: str = ""
