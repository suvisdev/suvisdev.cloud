from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.object_detection_dto import Detection


class ObjectDetectionPort(ABC):
    """물체 감지 아웃바운드 포트 (ABC) — Argus."""

    @abstractmethod
    def detect(self, image: bytes) -> list[Detection]:
        """이미지에서 객체를 감지해 Detection 목록을 반환한다."""
