"""영상 분류 포트 — labs 참조 구현.

이 Protocol은 참조 구현일 뿐이다. 실제 앱에 편입할 때는 그 앱의
app/ports/output/ 컨벤션(네이밍, 예외 타입, 동기/비동기 여부 등)에 맞춰
재배치한다. DTO(VideoClassificationResult/LabelScore)는 도메인 중립이라
그대로 재사용 가능하다(labs/README.md 참고).
"""

from __future__ import annotations

from typing import Protocol

from labs.video_classification.dto import VideoClassificationResult


class VideoClassificationPort(Protocol):
    def classify(self, video_bytes: bytes, *, top_k: int = 5) -> VideoClassificationResult:
        """영상에서 top-k 행동 레이블을 점수 내림차순으로 반환한다."""
        ...
