from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """감지된 단일 객체 — label, bbox(cx,cy,w,h 정규화 0~1), confidence."""

    label: str
    bbox: tuple[float, float, float, float]
    confidence: float
