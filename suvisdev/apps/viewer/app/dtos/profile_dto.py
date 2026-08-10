from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProfileDto:
    id: int
    username: str
    nickname: str
    email: str
    gender: str
    preferred_genres: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    # avatar_key는 S3 객체 key, avatar_url은 그 key로 발급한 presigned URL(1시간).
    # url은 저장값이 아니라 조회 시점에 채워지는 파생값이라 둘 다 들고 있는다.
    avatar_key: str | None = None
    avatar_url: str | None = None
