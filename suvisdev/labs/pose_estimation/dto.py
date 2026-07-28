"""자세 추정 결과 DTO — 도메인 중립.

좌표·신뢰도 같은 순수 데이터만 담는다. mova/gildle 등 특정 앱에 종속된
필드(예: movie_id, passenger_id)는 넣지 않는다 — 그래야 실제 앱에 편입할 때
그대로 재사용할 수 있다(labs/README.md 참고).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Keypoint:
    name: str
    x: float
    y: float
    confidence: float


@dataclass(frozen=True)
class PoseResult:
    """이미지에서 검출된 사람 1명의 자세."""

    keypoints: list[Keypoint]
    box_confidence: float
