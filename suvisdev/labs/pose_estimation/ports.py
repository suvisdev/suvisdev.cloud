"""자세 추정 포트 — labs 참조 구현.

이 Protocol은 참조 구현일 뿐이다. 실제 앱에 편입할 때는 그 앱의
app/ports/output/ 컨벤션(네이밍, 예외 타입, 동기/비동기 여부 등)에 맞춰
재배치한다. DTO(PoseResult/Keypoint)는 도메인 중립이라 그대로 재사용
가능하다(labs/README.md 참고).
"""

from __future__ import annotations

from typing import Protocol

from labs.pose_estimation.dto import PoseResult


class PoseEstimationPort(Protocol):
    def estimate(self, image_bytes: bytes) -> list[PoseResult]:
        """이미지에서 검출된 사람들의 자세를 반환한다(없으면 빈 리스트)."""
        ...
