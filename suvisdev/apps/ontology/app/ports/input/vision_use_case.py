from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.adapter.inbound.api.schemas.vision_schema import VisionIntroduceSchema
from ontology.app.dtos.vision_dto import VisionIntroduceResponse, VisionUploadResponse


class VisionUseCase(ABC):
    """vision 입력 포트 (ABC)."""

    @abstractmethod
    async def introduce_myself(
        self,
        schemas: VisionIntroduceSchema,
    ) -> VisionIntroduceResponse:
        pass

    @abstractmethod
    async def upload_image(
        self,
        filename: str,
        content: bytes,
    ) -> VisionUploadResponse:
        pass
