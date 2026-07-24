from __future__ import annotations

import asyncio
import logging
import mimetypes
from datetime import datetime

from core.matrix.aws_tank_s3_manager import get_tank
from ontology.app.dtos.vision_dto import (
    VisionImageCommand,
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionUploadResponse,
)
from ontology.app.ports.output.vision_port import VisionPort

logger = logging.getLogger(__name__)


class VisionS3Repository(VisionPort):
    def __init__(self) -> None:
        # S3 접근은 Tank(core)로 단일화 — 버킷/리전/자격증명(기본 체인)은 Tank가 관리.
        self._tank = get_tank()

    async def introduce_myself(self, query: VisionIntroduceQuery) -> VisionIntroduceResponse:
        logger.info("[VisionS3Repository] introduce_myself 진입 | request_data=%s", query)
        return VisionIntroduceResponse(
            id=query.id * 10000,
            name=query.name + "가 레포지토리에 다녀옴",
        )

    async def save_image(self, command: VisionImageCommand) -> VisionUploadResponse:
        # 키 네이밍·콘텐츠 타입은 도메인 로직이라 여기서, 실제 S3 put은 Tank에 위임한다.
        key = f"vision/{datetime.now():%Y%m%d_%H%M%S}_{command.filename}"
        content_type = mimetypes.guess_type(command.filename)[0] or "application/octet-stream"

        # Tank.upload_bytes는 동기 — 이벤트 루프 블로킹 방지. 버킷 미설정·boto 오류는
        # Tank가 RuntimeError로 감싸므로 여기서 별도 처리하지 않는다.
        url = await asyncio.to_thread(
            self._tank.upload_bytes, key, command.content, content_type=content_type
        )
        logger.info("[VisionS3Repository] save_image 완료 | key=%s", key)
        return VisionUploadResponse(
            filename=command.filename,
            size_bytes=len(command.content),
            saved_path=url,
        )
