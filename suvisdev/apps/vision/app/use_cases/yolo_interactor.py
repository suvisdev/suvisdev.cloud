from __future__ import annotations

from vision.app.dtos.face_dto import FacePredictResult, FaceTrainResult
from vision.app.ports.input.face_use_case import FaceUseCase
from vision.app.ports.output.face_dataset_port import FaceDatasetPort
from vision.app.ports.output.yolo_port import YoloPort

_AUTO_TRAIN_EPOCHS = 30
_AUTO_TRAIN_BATCH = 8
_AUTO_TRAIN_IMGSZ = 224


class YoloInteractor(FaceUseCase):
    """face_router → 입력 포트 → 출력 포트(dataset, yolo) → YOLO 분류 모델 파인튜닝·추론."""

    def __init__(self, dataset_port: FaceDatasetPort, yolo_port: YoloPort) -> None:
        self._dataset_port = dataset_port
        self._yolo_port = yolo_port

    def train(self, epochs: int, batch: int, imgsz: int) -> FaceTrainResult:
        dataset_root = self._dataset_port.get_dataset_root()
        return self._yolo_port.train(
            dataset_root=dataset_root,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
        )

    def predict(self, image_bytes: bytes) -> FacePredictResult:
        if not self._yolo_port.has_trained_weights():
            self.train(epochs=_AUTO_TRAIN_EPOCHS, batch=_AUTO_TRAIN_BATCH, imgsz=_AUTO_TRAIN_IMGSZ)
        return self._yolo_port.predict(image_bytes)
