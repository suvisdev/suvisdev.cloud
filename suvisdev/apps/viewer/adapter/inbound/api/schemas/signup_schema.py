from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class SignupUserSchema(BaseModel):
    """USERS — 로그인 + 프로필 (구 members 흡수)."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)
    nickname: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=1, max_length=255)
    gender: str = Field(default="undisclosed", max_length=32)
    age_group: str = Field(default="undisclosed", max_length=32)
    birth_year: int | None = None
    preferred_genres: list[str] | None = None
    bio: str | None = None


class SignupMemberSchema(BaseModel):
    """하위 호환 — 요청의 member 블록을 user 프로필로 병합."""

    gender: str = Field(default="undisclosed", max_length=32)
    age_group: str = Field(default="undisclosed", max_length=32)
    birth_year: int | None = None
    preferred_genres: list[str] | None = None
    bio: str | None = None


class SignupSchema(BaseModel):
    """회원가입: users 한 테이블 (프로필 포함)."""

    user: SignupUserSchema
    member: SignupMemberSchema = Field(default_factory=SignupMemberSchema)

    @model_validator(mode="before")
    @classmethod
    def _accept_flat_payload(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        if "user" in values or "member" in values:
            return values
        return {
            "user": {
                "username": values.get("username"),
                "password": values.get("password"),
                "nickname": values.get("nickname"),
                "email": values.get("email"),
                "gender": values.get("gender", "undisclosed"),
                "age_group": values.get("age_group", "undisclosed"),
                "birth_year": values.get("birth_year"),
                "preferred_genres": values.get("preferred_genres"),
                "bio": values.get("bio"),
            },
        }

    @model_validator(mode="after")
    def _merge_member_into_user(self) -> SignupSchema:
        merged = self.user.model_copy(
            update={
                "gender": self.member.gender or self.user.gender,
                "age_group": self.member.age_group or self.user.age_group,
                "birth_year": self.member.birth_year or self.user.birth_year,
                "preferred_genres": self.member.preferred_genres or self.user.preferred_genres,
                "bio": self.member.bio or self.user.bio,
            },
        )
        object.__setattr__(self, "user", merged)
        return self

    def log_summary(self) -> dict[str, str]:
        return {"username": self.user.username}
