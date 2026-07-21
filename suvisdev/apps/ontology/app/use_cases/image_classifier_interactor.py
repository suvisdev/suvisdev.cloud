from __future__ import annotations

from ontology.app.dtos.image_classifier_dto import Prediction
from ontology.app.ports.input.image_classifier_use_case import ImageClassifierUseCase
from ontology.app.ports.output.image_classifier_port import ImageClassifierPort


class ImageClassifierInteractor(ImageClassifierUseCase):
    """image_classifier_router → 입력 포트 → 출력 포트(ConvNeXt) → 포스터 장르 분류."""

    def __init__(self, classifier_port: ImageClassifierPort) -> None:
        self._classifier_port = classifier_port

    def classify(self, image: bytes) -> list[Prediction]:
        return self._classifier_port.classify(image)

    def supported_classes(self) -> list[str]:
        return self._classifier_port.supported_classes()
