from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentArea:
    """단일 클래스의 픽셀 점유 비율."""

    class_name: str
    area_ratio: float


@dataclass(frozen=True)
class SegmentationResult:
    """전체 분할 결과 — 클래스별 면적 비율 + (선택) 마스크 오버레이 base64."""

    areas: tuple[SegmentArea, ...]
    mask_b64: str = ""
