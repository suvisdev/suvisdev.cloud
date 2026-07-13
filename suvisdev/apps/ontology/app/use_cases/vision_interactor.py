from __future__ import annotations

from ontology.adapter.inbound.api.schemas.vision_schema import VisionIntroduceSchema
from ontology.app.dtos.vision_dto import (
    VisionImageCommand,
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionUploadResponse,
)
from ontology.app.ports.input.vision_use_case import VisionUseCase
from ontology.app.ports.output.vision_port import VisionPort

_ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")


class VisionInteractor(VisionUseCase):
    """vision_router → 입력 포트 → 출력 포트(repository)."""

    def __init__(self, repository: VisionPort) -> None:
        self._repository = repository

    async def introduce_myself(
        self,
        schemas: VisionIntroduceSchema,
    ) -> VisionIntroduceResponse:
        return await self._repository.introduce_myself(
            VisionIntroduceQuery(id=schemas.id, name=schemas.name),
        )

    async def upload_image(
        self,
        filename: str,
        content: bytes,
    ) -> VisionUploadResponse:
        if not filename.lower().endswith(_ALLOWED_EXTENSIONS):
            raise ValueError("JPG 또는 PNG 이미지 파일만 업로드할 수 있습니다.")
        if not content:
            raise ValueError("빈 파일입니다.")
        return await self._repository.save_image(
            VisionImageCommand(filename=filename, content=content),
        )
