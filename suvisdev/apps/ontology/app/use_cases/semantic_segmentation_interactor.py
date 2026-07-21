from __future__ import annotations

from ontology.app.dtos.semantic_segmentation_dto import SegmentationResult
from ontology.app.ports.input.semantic_segmentation_use_case import SemanticSegmentationUseCase
from ontology.app.ports.output.semantic_segmentation_port import SemanticSegmentationPort


class SemanticSegmentationInteractor(SemanticSegmentationUseCase):
    """semantic_segmentation_router → 입력 포트 → 출력 포트(SegFormer-B0) → 시맨틱 분할."""

    def __init__(self, segmenter_port: SemanticSegmentationPort) -> None:
        self._segmenter_port = segmenter_port

    def segment(self, image: bytes) -> SegmentationResult:
        return self._segmenter_port.segment(image)
