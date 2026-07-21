from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult


class AnomalyDetectionPort(ABC):
    """이상 탐지 아웃바운드 포트 (ABC) — Sentinel."""

    @abstractmethod
    def detect(self, image: bytes) -> AnomalyResult:
        """이미지가 정상인지 이상인지 판정하고 점수와 히트맵을 반환한다."""
