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
