"""시맨틱 분할 결과 DTO — 도메인 중립.

픽셀 마스크·클래스 라벨·신뢰도 같은 순수 데이터만 담는다. "서울 보도"처럼
특정 용도에 종속된 필드는 넣지 않는다 — 그래야 실제 앱에 편입할 때 그대로
재사용할 수 있다(labs/README.md 참고).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedClass:
    """마스크에서 검출된 클래스 1개 요약."""

    label: str
    class_id: int
    pixel_count: int
    confidence: float  # 이 클래스로 분류된 픽셀들의 평균 softmax 확신도


@dataclass(frozen=True)
class SegmentationResult:
    width: int
    height: int
    class_mask: list[list[int]]  # class_mask[y][x] = class_id
    detected_classes: list[DetectedClass]
