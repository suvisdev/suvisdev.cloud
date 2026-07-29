from fastapi import Depends

from ontology.adapter.outbound.repositories.vision_repository import VisionRepository
from ontology.app.ports.input.vision_use_case import VisionUseCase
from ontology.app.ports.output.vision_port import VisionPort
from ontology.app.use_cases.vision_interactor import VisionInteractor
from ontology.dependencies.anomaly_detection_provider import get_anomaly_detection_port


def get_vision_repository() -> VisionPort:
    # S3(VisionS3Repository)는 AWS 자격증명 미연결로 보류 — 소프트 플래그
    # 지속화까지 필요해져 DB 폴백(VisionRepository)을 기본 배선으로 전환.
    return VisionRepository()


def get_vision_use_case(
    repository: VisionPort = Depends(get_vision_repository),
) -> VisionUseCase:
    return VisionInteractor(repository=repository, anomaly_port=get_anomaly_detection_port())
