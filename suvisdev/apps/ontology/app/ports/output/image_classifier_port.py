from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.image_classifier_dto import Prediction


class ImageClassifierPort(ABC):
    """이미지 분류 추론 아웃바운드 포트 (ABC)."""

    @abstractmethod
    def classify(self, image: bytes) -> list[Prediction]:
        """이미지를 분류해 신뢰도 내림차순 top-k Prediction 목록을 반환한다."""

    @abstractmethod
    def supported_classes(self) -> list[str]:
        """이 분류기가 인식 가능한 클래스 라벨 목록을 반환한다."""
