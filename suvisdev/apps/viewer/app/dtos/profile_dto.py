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
