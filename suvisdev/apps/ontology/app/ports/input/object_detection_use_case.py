from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.object_detection_dto import Detection


class ObjectDetectionUseCase(ABC):
    """물체 감지 입력 포트 (ABC) — Argus."""

    @abstractmethod
    def detect(self, image: bytes) -> list[Detection]:
        pass
