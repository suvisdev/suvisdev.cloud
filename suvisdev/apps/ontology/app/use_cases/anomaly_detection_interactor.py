from __future__ import annotations

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult
from ontology.app.ports.input.anomaly_detection_use_case import AnomalyDetectionUseCase
from ontology.app.ports.output.anomaly_detection_port import AnomalyDetectionPort


class AnomalyDetectionInteractor(AnomalyDetectionUseCase):
    """anomaly_detection_router → 입력 포트 → 출력 포트(PatchCore/EfficientAD) → 이상 탐지."""

    def __init__(self, detector_port: AnomalyDetectionPort) -> None:
        self._detector_port = detector_port

    def detect(self, image: bytes) -> AnomalyResult:
        return self._detector_port.detect(image)
