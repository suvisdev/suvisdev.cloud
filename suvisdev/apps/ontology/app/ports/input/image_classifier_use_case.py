from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.image_classifier_dto import Prediction


class ImageClassifierUseCase(ABC):
    """이미지 분류 입력 포트 (ABC)."""

    @abstractmethod
    def classify(self, image: bytes) -> list[Prediction]:
        pass

    @abstractmethod
    def supported_classes(self) -> list[str]:
        pass
