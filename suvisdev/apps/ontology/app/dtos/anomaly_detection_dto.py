from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyResult:
    """이상 탐지 결과 — 점수·판정·히트맵(선택)."""

    anomaly_score: float
    is_anomaly: bool
    heatmap_b64: str = ""
