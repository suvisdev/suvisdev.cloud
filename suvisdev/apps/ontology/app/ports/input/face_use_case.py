from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.face_dto import FacePredictResult, FaceTrainResult


class FaceUseCase(ABC):
    """얼굴 인식 입력 포트 (ABC)."""

    @abstractmethod
    def train(self, epochs: int, batch: int, imgsz: int) -> FaceTrainResult:
        pass

    @abstractmethod
    def predict(self, image_bytes: bytes) -> FacePredictResult:
        pass
