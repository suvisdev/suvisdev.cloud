"""태그 도메인 Value Objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TagKind(str, Enum):
    """태그 분류 — 감성/장르/등장인물."""

    MOOD = "mood"
    GENRE = "genre"
    CAST = "cast"

    @classmethod
    def from_str(cls, value: str | None) -> TagKind:
        for member in cls:
            if member.value == value:
                return member
        return cls.MOOD

    def label_ko(self) -> str:
        return {"mood": "감성", "genre": "장르", "cast": "등장인물"}[self.value]


@dataclass(frozen=True)
class TagSlug:
    """태그 slug.

    mood: 공유 slug (예: 'heartwarming')
    genre: 'genre-{장르}' (예: 'genre-sf')
    cast: 'cast-{이름}' (예: 'cast-전지현')
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("TagSlug cannot be empty")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def for_genre(cls, genre: str) -> TagSlug:
        return cls(f"genre-{genre.strip().lower()}")

    @classmethod
    def for_cast(cls, name: str) -> TagSlug:
        return cls(f"cast-{name.strip()}")


if __name__ == "__main__":
    assert TagKind.from_str("genre") == TagKind.GENRE
    assert TagKind.CAST.label_ko() == "등장인물"

    slug = TagSlug.for_genre("SF")
    assert str(slug) == "genre-sf"

    cast_slug = TagSlug.for_cast("전지현")
    assert str(cast_slug) == "cast-전지현"

    try:
        TagSlug("")
        assert False
    except ValueError:
        pass

    print("studio_tags_vo OK")
