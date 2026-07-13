from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ontology.app.dtos.face_dto import FacePredictResult, FaceTrainResult


class YoloPort(ABC):
    """YOLO 모델 파인튜닝·추론 아웃바운드 포트 (ABC)."""

    @abstractmethod
    def train(
        self,
        dataset_root: Path,
        epochs: int,
        batch: int,
        imgsz: int,
    ) -> FaceTrainResult:
        pass

    @abstractmethod
    def has_trained_weights(self) -> bool:
        pass

    @abstractmethod
    def predict(self, image_bytes: bytes) -> FacePredictResult:
        pass
