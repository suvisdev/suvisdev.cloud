"""영화 도메인 Value Objects + canonical slug 유틸."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ── canonical slug 매핑 (기존 유지) ─────────────────────────────────────────
TITLE_TO_CANONICAL_SLUG: dict[str, str] = {
    "원더풀스": "wonderfuls",
    "암살": "assassination",
    "인터스텔라": "interstellar",
    "듄: 파트2": "dune-2",
    "오펜하이머": "oppenheimer",
    "기생충": "parasite",
    "블레이드 러너 2049": "blade-runner-2049",
    "라라랜드": "lalaland",
    "매트릭스": "matrix",
    "인셉션": "inception",
    "다크 나이트": "dark-knight",
    "오징어 게임": "squid-game",
}


def resolve_canonical_slug(key: str, *, title: str | None = None) -> str:
    k = key.strip()
    if not k and title:
        k = title.strip()
    if k in TITLE_TO_CANONICAL_SLUG:
        return TITLE_TO_CANONICAL_SLUG[k]
    if title:
        t = title.strip()
        if t in TITLE_TO_CANONICAL_SLUG:
            return TITLE_TO_CANONICAL_SLUG[t]
    return k or "movie"


def title_for_canonical_slug(canonical: str) -> str | None:
    for title, slug in TITLE_TO_CANONICAL_SLUG.items():
        if slug == canonical.strip():
            return title
    return None


# ── Value Objects ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MovieSlug:
    """영화 URL 식별자. 빈 문자열 불가."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("MovieSlug cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PlatformEntry:
    """OTT 플랫폼 항목 — platforms JSONB 배열의 원소.

    provider: 'netflix' | 'disney' | 'watcha' 등
    url: 플랫폼 직접 링크 (nullable)
    type: 'subscription' | 'rent' | 'buy' (nullable)
    """

    provider: str
    url: str | None = None
    type: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> PlatformEntry:
        return cls(
            provider=d.get("provider", ""),
            url=d.get("url"),
            type=d.get("type"),
        )

    def to_dict(self) -> dict:
        return {"provider": self.provider, "url": self.url, "type": self.type}


class AgeRating(str, Enum):
    """영화 관람 등급."""

    ALL = "전체"
    TWELVE = "12세"
    FIFTEEN = "15세"
    ADULT = "청불"

    @classmethod
    def from_str(cls, value: str | None) -> AgeRating | None:
        if value is None:
            return None
        for member in cls:
            if member.value == value:
                return member
        return None


if __name__ == "__main__":
    slug = MovieSlug("interstellar")
    assert str(slug) == "interstellar"

    pe = PlatformEntry.from_dict({"provider": "netflix", "url": None, "type": "subscription"})
    assert pe.provider == "netflix"
    assert pe.to_dict()["type"] == "subscription"

    ar = AgeRating.from_str("12세")
    assert ar == AgeRating.TWELVE
    assert AgeRating.from_str(None) is None

    print("studio_movies_vo OK")
