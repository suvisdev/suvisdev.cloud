"""아바타 이미지를 S3에 넣고 표시용 presigned URL을 발급한다.

media 앱에도 S3 업로드 경로(`POST /media/photos`)가 있지만 재사용하지 않는다 —
그쪽은 susu(Flutter)의 RS256 `aud=suvis-susu` 토큰 전용이고, media·viewer 둘 다
Spoke라 직접 import가 금지돼 있다(suvisdev/CLAUDE.md O.4). 공용 자원인
`core.matrix.aws_tank_s3_manager`만 함께 쓴다.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from core.matrix.aws_tank_s3_manager import get_tank
from viewer.app.ports.output.avatar_storage import AvatarStorage

logger = logging.getLogger(__name__)

_URL_TTL_SECONDS = 3600


class TankAvatarStorageAdapter(AvatarStorage):
    async def upload(self, user_id: int, data: bytes, *, content_type: str, ext: str) -> str:
        # susu가 쓰는 media/ 아래와 섞이지 않도록 avatars/ prefix로 분리한다.
        key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"
        tank = get_tank()
        # boto3는 동기 라이브러리라 이벤트 루프를 막지 않도록 스레드로 넘긴다.
        await asyncio.to_thread(tank.upload_bytes, key, data, content_type=content_type)
        return key

    def build_url(self, key: str) -> str | None:
        try:
            return get_tank().generate_presigned_url(key, expires_in=_URL_TTL_SECONDS)
        except RuntimeError:
            # URL 발급 실패로 프로필 조회 전체를 막지 않는다 — 아바타만 안 보인다.
            logger.exception("[avatar] presigned URL 발급 실패 | key=%s", key)
            return None
