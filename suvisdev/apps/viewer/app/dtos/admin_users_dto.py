from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viewer.adapter.inbound.api.schemas.admin_users_schema import UserAdminSchema


@dataclass
class UserAdminDto:
    id: int
    email: str
    nickname: str
    role: str  # "admin" | "user"
    providers: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_schema(self) -> UserAdminSchema:
        from viewer.adapter.inbound.api.schemas.admin_users_schema import UserAdminSchema

        return UserAdminSchema(
            id=self.id,
            email=self.email,
            nickname=self.nickname,
            role=self.role,
            providers=self.providers,
            created_at=self.created_at.isoformat(),
        )
