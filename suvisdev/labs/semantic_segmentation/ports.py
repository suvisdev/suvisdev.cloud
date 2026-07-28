"""시맨틱 분할 포트 — labs 참조 구현.

이 Protocol은 참조 구현일 뿐이다. 실제 앱에 편입할 때는 그 앱의
app/ports/output/ 컨벤션(네이밍, 예외 타입, 동기/비동기 여부 등)에 맞춰
재배치한다. DTO(SegmentationResult/DetectedClass)는 도메인 중립이라 그대로
재사용 가능하다(labs/README.md 참고).
"""

from __future__ import annotations

from typing import Protocol

from labs.semantic_segmentation.dto import SegmentationResult


class SemanticSegmentationPort(Protocol):
    def segment(self, image_bytes: bytes) -> SegmentationResult:
        """이미지를 픽셀 단위로 분할해 클래스 마스크를 반환한다."""
        ...
