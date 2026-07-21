from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Keypoint:
    """관절 하나 — 좌표(픽셀 정규화 0~1)와 가시성 플래그."""

    x: float
    y: float
    visibility: float


@dataclass(frozen=True)
class PersonPose:
    """한 사람의 자세 — 관절 목록 + 전체 신뢰도."""

    keypoints: tuple[Keypoint, ...]
    confidence: float
