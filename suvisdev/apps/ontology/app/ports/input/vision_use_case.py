from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.vision_dto import (
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionUploadResponse,
)


class VisionUseCase(ABC):
    """vision 입력 포트 (ABC)."""

    @abstractmethod
    async def introduce_myself(
        self,
        query: VisionIntroduceQuery,
    ) -> VisionIntroduceResponse:
        pass

    @abstractmethod
    async def upload_image(
        self,
        filename: str,
        content: bytes,
    ) -> VisionUploadResponse:
        pass
