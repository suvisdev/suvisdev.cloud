from __future__ import annotations

from pydantic import BaseModel, Field


class LoginSchema(BaseModel):
    """USERS 기반 로그인 요청 스키마."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)

    def log_summary(self) -> dict[str, str]:
        return {"username": self.username}
