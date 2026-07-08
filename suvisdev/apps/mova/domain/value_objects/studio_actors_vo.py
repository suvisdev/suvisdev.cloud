"""배우/감독 도메인 Value Objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RoleType(str, Enum):
    """인물 역할 — 배우(출연) 또는 감독."""

    DIRECTOR = "director"
    ACTOR = "actor"

    @classmethod
    def from_str(cls, value: str | None) -> RoleType:
        if value == "director":
            return cls.DIRECTOR
        return cls.ACTOR

    def label_ko(self) -> str:
        return "감독" if self == RoleType.DIRECTOR else "배우"


@dataclass(frozen=True)
class ActorName:
    """인물 이름 — 빈 문자열 불가."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("ActorName cannot be empty")

    def __str__(self) -> str:
        return self.value


if __name__ == "__main__":
    assert RoleType.from_str("director") == RoleType.DIRECTOR
    assert RoleType.from_str("actor") == RoleType.ACTOR
    assert RoleType.DIRECTOR.label_ko() == "감독"

    name = ActorName("전지현")
    assert str(name) == "전지현"

    try:
        ActorName("")
        assert False, "should raise"
    except ValueError:
        pass

    print("studio_actors_vo OK")
