from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.semantic_segmentation_dto import SegmentationResult


class SemanticSegmentationPort(ABC):
    """시맨틱 분할 아웃바운드 포트 (ABC) — Loom."""

    @abstractmethod
    def segment(self, image: bytes) -> SegmentationResult:
        """이미지를 픽셀 단위로 분할해 클래스별 면적 비율과 마스크를 반환한다."""
