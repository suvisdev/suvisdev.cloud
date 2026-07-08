from fastapi import Depends

from vision.adapter.outbound.repositories.vision_s3_repository import VisionS3Repository
from vision.app.ports.input.vision_use_case import VisionUseCase
from vision.app.ports.output.vision_port import VisionPort
from vision.app.use_cases.vision_interactor import VisionInteractor


def get_vision_repository() -> VisionPort:
    return VisionS3Repository()


def get_vision_use_case(
    repository: VisionPort = Depends(get_vision_repository),
) -> VisionUseCase:
    return VisionInteractor(repository=repository)
