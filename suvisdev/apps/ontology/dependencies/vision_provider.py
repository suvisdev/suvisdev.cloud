from fastapi import Depends

from ontology.adapter.outbound.repositories.vision_s3_repository import VisionS3Repository
from ontology.app.ports.input.vision_use_case import VisionUseCase
from ontology.app.ports.output.vision_port import VisionPort
from ontology.app.use_cases.vision_interactor import VisionInteractor
from ontology.dependencies.anomaly_detection_provider import get_anomaly_detection_port


def get_vision_repository() -> VisionPort:
    return VisionS3Repository()


def get_vision_use_case(
    repository: VisionPort = Depends(get_vision_repository),
) -> VisionUseCase:
    return VisionInteractor(repository=repository, anomaly_port=get_anomaly_detection_port())
