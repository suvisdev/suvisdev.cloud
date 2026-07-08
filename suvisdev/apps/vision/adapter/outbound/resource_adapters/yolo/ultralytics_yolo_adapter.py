from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from ultralytics import YOLO

from vision.app.dtos.face_dto import FacePredictResult, FaceTrainResult
from vision.app.ports.output.yolo_port import YoloPort

_RUNS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "runs"
_WEIGHTS_PATH = _RUNS_DIR / "face_classify" / "weights" / "best.pt"


class UltralyticsYoloAdapter(YoloPort):
    """YOLOv11 Nano(yolo11n-cls) 파인튜닝·추론 — ultralytics 라이브러리 종속성을 이 어댑터에 격리한다."""

    def train(
        self,
        dataset_root: Path,
        epochs: int,
        batch: int,
        imgsz: int,
    ) -> FaceTrainResult:
        model = YOLO("yolo11n-cls.pt")
        results = model.train(
            data=str(dataset_root),
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            project=str(_RUNS_DIR),
            name="face_classify",
            exist_ok=True,
        )

        return FaceTrainResult(
            weights_path=str(results.save_dir / "weights" / "best.pt"),
            class_names=list(model.names.values()),
            epochs=epochs,
        )

    def has_trained_weights(self) -> bool:
        return _WEIGHTS_PATH.is_file()

    def predict(self, image_bytes: bytes) -> FacePredictResult:
        model = YOLO(str(_WEIGHTS_PATH))
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = model.predict(source=image, verbose=False)

        probs = results[0].probs
        top1_index = int(probs.top1)
        return FacePredictResult(
            predicted_name=model.names[top1_index],
            confidence=float(probs.top1conf),
        )
