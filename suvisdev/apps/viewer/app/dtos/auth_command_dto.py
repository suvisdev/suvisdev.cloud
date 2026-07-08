from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viewer.adapter.inbound.api.schemas.login_schema import LoginSchema
    from viewer.adapter.inbound.api.schemas.signup_schema import SignupSchema


@dataclass
class LoginUserCommand:
    username: str
    password: str

    @classmethod
    def from_schema(cls, payload: LoginSchema) -> LoginUserCommand:
        return cls(username=payload.username, password=payload.password)


@dataclass
class SignupUserCommand:
    username: str
    password: str
    nickname: str
    email: str
    gender: str
    age_group: str
    birth_year: int | None
    preferred_genres: list[str] | None
    bio: str | None


@dataclass
class SignupCommand:
    user: SignupUserCommand

    @classmethod
    def from_schema(cls, payload: SignupSchema) -> SignupCommand:
        user = payload.user
        return cls(
            user=SignupUserCommand(
                username=user.username,
                password=user.password,
                nickname=user.nickname,
                email=user.email,
                gender=user.gender,
                age_group=user.age_group,
                birth_year=user.birth_year,
                preferred_genres=user.preferred_genres,
                bio=user.bio,
            ),
        )


@dataclass
class LoginResponseDto:
    user_id: int
    username: str


@dataclass
class SignupResponseDto:
    user_id: int
