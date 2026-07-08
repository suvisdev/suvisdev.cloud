from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class FaceDatasetPort(ABC):
    """얼굴 인식 학습 데이터셋 아웃바운드 포트 (ABC)."""

    @abstractmethod
    def get_dataset_root(self) -> Path:
        """train/val 서브폴더를 포함하는 데이터셋 루트 경로를 반환한다."""
