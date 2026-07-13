from pathlib import Path

from ontology.adapter.outbound.resource_adapters.yolo.local_face_dataset_repository import (
    LocalFaceDatasetRepository,
)
from ontology.adapter.outbound.resource_adapters.yolo.ultralytics_yolo_adapter import (
    UltralyticsYoloAdapter,
)
from ontology.app.ports.input.face_use_case import FaceUseCase
from ontology.app.ports.output.face_dataset_port import FaceDatasetPort
from ontology.app.ports.output.yolo_port import YoloPort
from ontology.app.use_cases.yolo_interactor import YoloInteractor

_DATASET_ROOT = Path(__file__).resolve().parent.parent / "resources" / "yolo_train"


def get_face_dataset_repository() -> FaceDatasetPort:
    return LocalFaceDatasetRepository(base_path=_DATASET_ROOT)


def get_yolo_port() -> YoloPort:
    return UltralyticsYoloAdapter()


def get_face_use_case() -> FaceUseCase:
    return YoloInteractor(
        dataset_port=get_face_dataset_repository(),
        yolo_port=get_yolo_port(),
    )
