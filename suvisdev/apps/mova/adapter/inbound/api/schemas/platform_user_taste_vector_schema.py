"""유저 취향 벡터 조회 응답 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserTasteVectorSchema(BaseModel):
    """원본 768차원 벡터는 노출하지 않는다 — 내부 코사인 계산 전용이라 표시 가치가
    없고, 소비할 프론트 화면도 아직 없다. 상태 확인용 메타데이터만 반환한다.
    """

    has_vector: bool
    review_count: int
    updated_at: datetime | None
