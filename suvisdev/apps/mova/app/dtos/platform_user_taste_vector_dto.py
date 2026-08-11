"""유저 취향 벡터 DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserTasteVectorDto:
    user_id: int
    vector: list[float] | None
    review_count: int
    updated_at: datetime

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.platform_user_taste_vector_schema import (
            UserTasteVectorSchema,
        )

        return UserTasteVectorSchema(
            has_vector=self.vector is not None,
            review_count=self.review_count,
            updated_at=self.updated_at,
        )
