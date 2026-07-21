from __future__ import annotations

from ontology.app.dtos.object_detection_dto import Detection
from ontology.app.ports.input.object_detection_use_case import ObjectDetectionUseCase
from ontology.app.ports.output.object_detection_port import ObjectDetectionPort


class ObjectDetectionInteractor(ObjectDetectionUseCase):
    """object_detection_router → 입력 포트 → 출력 포트(YOLOv8/RT-DETR) → 물체 감지."""

    def __init__(self, detector_port: ObjectDetectionPort) -> None:
        self._detector_port = detector_port

    def detect(self, image: bytes) -> list[Detection]:
        return self._detector_port.detect(image)
