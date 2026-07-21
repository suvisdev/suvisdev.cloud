from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.video_classification_dto import VideoPrediction


class VideoClassificationPort(ABC):
    """동영상 분류 아웃바운드 포트 (ABC) — Chronos."""

    @abstractmethod
    def classify(self, video: bytes) -> list[VideoPrediction]:
        """영상 클립을 분류해 신뢰도 내림차순 top-k VideoPrediction 목록을 반환한다."""
