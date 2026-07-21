from __future__ import annotations

from pydantic import BaseModel


class UserAdminSchema(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    providers: list[str]
    created_at: str
