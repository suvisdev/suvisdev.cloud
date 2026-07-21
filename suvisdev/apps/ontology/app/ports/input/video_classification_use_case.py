from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.video_classification_dto import VideoPrediction


class VideoClassificationUseCase(ABC):
    """동영상 분류 입력 포트 (ABC) — Chronos."""

    @abstractmethod
    def classify(self, video: bytes) -> list[VideoPrediction]:
        pass
