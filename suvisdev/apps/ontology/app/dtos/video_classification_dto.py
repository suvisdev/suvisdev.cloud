from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoPrediction:
    """동영상 분류 결과 단일 항목 — label·confidence."""

    label: str
    confidence: float
