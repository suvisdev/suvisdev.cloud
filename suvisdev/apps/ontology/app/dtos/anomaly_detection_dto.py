from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyResult:
    """이상 탐지 결과 — CLIP 제로샷(포스터 여부) + Laplacian variance(블러 여부).

    06_anomaly_detection_agent.md §6.5 방향 결정: PatchCore(단일
    anomaly_score/heatmap)는 포스터 도메인에 부적합해 기각, 신호가 2개로
    분리됐다(포스터 여부 / 블러 여부).
    """

    is_poster: bool
    poster_confidence: float
    is_blurry: bool
    sharpness_score: float
