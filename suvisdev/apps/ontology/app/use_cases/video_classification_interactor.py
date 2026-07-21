from __future__ import annotations

from ontology.app.dtos.video_classification_dto import VideoPrediction
from ontology.app.ports.input.video_classification_use_case import VideoClassificationUseCase
from ontology.app.ports.output.video_classification_port import VideoClassificationPort


class VideoClassificationInteractor(VideoClassificationUseCase):
    """video_classification_router → 입력 포트 → 출력 포트(VideoMAE/X3D) → 동영상 분류."""

    def __init__(self, classifier_port: VideoClassificationPort) -> None:
        self._classifier_port = classifier_port

    def classify(self, video: bytes) -> list[VideoPrediction]:
        return self._classifier_port.classify(video)
