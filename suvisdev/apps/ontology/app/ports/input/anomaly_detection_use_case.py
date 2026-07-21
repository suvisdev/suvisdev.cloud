from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult


class AnomalyDetectionUseCase(ABC):
    """이상 탐지 입력 포트 (ABC) — Sentinel."""

    @abstractmethod
    def detect(self, image: bytes) -> AnomalyResult:
        pass
