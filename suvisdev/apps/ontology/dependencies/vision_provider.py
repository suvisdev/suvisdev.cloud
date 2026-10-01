from fastapi import Depends

from ontology.adapter.outbound.repositories.vision_repository import VisionRepository
from ontology.app.ports.input.vision_use_case import VisionUseCase
from ontology.app.ports.output.vision_port import VisionPort
from ontology.app.use_cases.vision_interactor import VisionInteractor
from ontology.dependencies.anomaly_detection_provider import get_anomaly_detection_port


def get_vision_repository() -> VisionPort:
    # 비전 결과는 DB(VisionRepository)에만 둔다 — S3 저장 어댑터는 쓰지 않기로 해 삭제(2026-10-01).
    return VisionRepository()


def get_vision_use_case(
    repository: VisionPort = Depends(get_vision_repository),
) -> VisionUseCase:
    return VisionInteractor(repository=repository, anomaly_port=get_anomaly_detection_port())
