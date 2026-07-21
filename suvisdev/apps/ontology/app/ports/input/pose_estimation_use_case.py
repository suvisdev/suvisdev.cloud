from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.pose_estimation_dto import PersonPose


class PoseEstimationUseCase(ABC):
    """자세 추정 입력 포트 (ABC) — Atlas."""

    @abstractmethod
    def estimate(self, image: bytes) -> list[PersonPose]:
        pass
