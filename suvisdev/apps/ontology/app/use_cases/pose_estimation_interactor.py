from __future__ import annotations

from ontology.app.dtos.pose_estimation_dto import PersonPose
from ontology.app.ports.input.pose_estimation_use_case import PoseEstimationUseCase
from ontology.app.ports.output.pose_estimation_port import PoseEstimationPort


class PoseEstimationInteractor(PoseEstimationUseCase):
    """pose_estimation_router → 입력 포트 → 출력 포트(ViTPose/RTMPose) → 자세 추정."""

    def __init__(self, pose_port: PoseEstimationPort) -> None:
        self._pose_port = pose_port

    def estimate(self, image: bytes) -> list[PersonPose]:
        return self._pose_port.estimate(image)
