from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.vision_dto import (
    VisionImageCommand,
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionPosterFlagOverrideDto,
    VisionUploadResponse,
)


class VisionPort(ABC):
    """vision 아웃바운드 포트 (ABC)."""

    @abstractmethod
    async def introduce_myself(self, query: VisionIntroduceQuery) -> VisionIntroduceResponse:
        pass

    @abstractmethod
    async def save_image(self, command: VisionImageCommand) -> VisionUploadResponse:
        pass

    @abstractmethod
    async def update_poster_flag(
        self, upload_id: int, is_poster_warning: bool
    ) -> VisionPosterFlagOverrideDto:
        pass
