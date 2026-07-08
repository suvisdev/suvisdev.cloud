from __future__ import annotations

from pathlib import Path

from vision.app.ports.output.face_dataset_port import FaceDatasetPort

_REQUIRED_SPLITS = ("train", "val")


class LocalFaceDatasetRepository(FaceDatasetPort):
    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def get_dataset_root(self) -> Path:
        for split in _REQUIRED_SPLITS:
            split_path = self._base_path / split
            if not split_path.is_dir():
                raise FileNotFoundError(
                    f"얼굴 데이터셋 '{split}' 폴더를 찾을 수 없습니다: {split_path}"
                )
        return self._base_path
