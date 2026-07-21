from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.semantic_segmentation_dto import SegmentationResult


class SemanticSegmentationUseCase(ABC):
    """시맨틱 분할 입력 포트 (ABC) — Loom."""

    @abstractmethod
    def segment(self, image: bytes) -> SegmentationResult:
        pass
