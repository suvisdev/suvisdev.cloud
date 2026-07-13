from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

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
        self._bucket = os.getenv("VISION_S3_BUCKET", "")
        self._region = os.getenv("AWS_REGION", "ap-northeast-2")
        self._client = boto3.client("s3", region_name=self._region)

    async def introduce_myself(self, query: VisionIntroduceQuery) -> VisionIntroduceResponse:
        logger.info("[VisionS3Repository] introduce_myself 진입 | request_data=%s", query)
        return VisionIntroduceResponse(
            id=query.id * 10000,
            name=query.name + "가 레포지토리에 다녀옴",
        )

    async def save_image(self, command: VisionImageCommand) -> VisionUploadResponse:
        if not self._bucket:
            raise RuntimeError("VISION_S3_BUCKET 환경변수가 설정되지 않았습니다.")

        key = f"vision/{datetime.now():%Y%m%d_%H%M%S}_{command.filename}"
        content_type = mimetypes.guess_type(command.filename)[0] or "application/octet-stream"

        try:
            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=command.content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as e:
            logger.exception("[VisionS3Repository] S3 업로드 실패 | key=%s", key)
            raise RuntimeError(f"S3 업로드 실패: {e}") from e

        logger.info("[VisionS3Repository] save_image 완료 | bucket=%s key=%s", self._bucket, key)
        return VisionUploadResponse(
            filename=command.filename,
            size_bytes=len(command.content),
            saved_path=f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}",
        )
