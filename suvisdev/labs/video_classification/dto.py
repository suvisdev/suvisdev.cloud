"""영상 분류 결과 DTO — 도메인 중립.

레이블·점수 같은 순수 데이터만 담는다. 특정 앱에 종속된 필드는 넣지 않는다
— 그래야 실제 앱에 편입할 때 그대로 재사용할 수 있다(labs/README.md 참고).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelScore:
    label: str
    score: float


@dataclass(frozen=True)
class VideoClassificationResult:
    """점수 내림차순으로 정렬된 top-k 예측."""

    predictions: list[LabelScore]
