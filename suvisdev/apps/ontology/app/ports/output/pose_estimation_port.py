from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.pose_estimation_dto import PersonPose


class PoseEstimationPort(ABC):
    """자세 추정 아웃바운드 포트 (ABC) — Atlas."""

    @abstractmethod
    def estimate(self, image: bytes) -> list[PersonPose]:
        """이미지 속 사람별 관절 키포인트를 추정해 PersonPose 목록을 반환한다."""
