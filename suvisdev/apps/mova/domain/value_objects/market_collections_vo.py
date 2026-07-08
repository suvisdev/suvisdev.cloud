"""컬렉션 도메인 Value Objects."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class CollectionSlug:
    """컬렉션 URL 식별자 (예: dark-knight-trilogy)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized or len(normalized) > 64:
            raise ValueError(f"CollectionSlug must be 1-64 chars: {self.value!r}")
        if not _SLUG_PATTERN.match(normalized):
            raise ValueError(f"CollectionSlug invalid format: {self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CollectionName:
    """컬렉션 표시 이름."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("CollectionName cannot be empty")
        if len(self.value) > 255:
            raise ValueError("CollectionName cannot exceed 255 chars")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CollectionDescription:
    """컬렉션 설명 — 빈 문자열 허용 (ERD default '')."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value or "")

    def is_empty(self) -> bool:
        return not self.value.strip()

    def __str__(self) -> str:
        return self.value


if __name__ == "__main__":
    slug = CollectionSlug("dark-knight-trilogy")
    assert str(slug) == "dark-knight-trilogy"

    name = CollectionName("다크 나이트 트릴로지")
    assert str(name) == "다크 나이트 트릴로지"

    desc = CollectionDescription("")
    assert desc.is_empty()

    filled = CollectionDescription("  시리즈 소개  ")
    assert not filled.is_empty()

    try:
        CollectionSlug("Bad Slug!")
        assert False, "should raise"
    except ValueError:
        pass

    print("market_collections_vo OK")
