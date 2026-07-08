"""영화 도메인 Entity — 도메인 규칙 캡슐화."""

from __future__ import annotations

from dataclasses import dataclass

from mova.domain.value_objects.studio_movies_vo import AgeRating, PlatformEntry


@dataclass(frozen=True)
class MovieEntity:
    """영화 카탈로그 도메인 객체.

    ORM · Pydantic에 의존하지 않는다.
    PK `id`는 Repository가 반환한 뒤에만 존재 — 신규 생성 시 0 허용.
    """

    id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    platforms: list[PlatformEntry]
    age_rating: AgeRating | None
    genres: list[str]
    collection_id: int | None

    @classmethod
    def from_orm(cls, orm: object) -> MovieEntity:
        """SQLAlchemy ORM row → Entity. ORM import는 이 팩토리 안에서만."""
        platforms = [
            PlatformEntry.from_dict(p) if isinstance(p, dict) else p
            for p in (getattr(orm, "platforms", None) or [])
        ]
        return cls(
            id=orm.id,
            slug=orm.slug,
            title=orm.title,
            release_year=orm.release_year or "",
            rating=orm.rating or 0.0,
            poster_url=orm.poster_url or "",
            platforms=platforms,
            age_rating=AgeRating.from_str(orm.age_rating),
            genres=list(orm.genres or []),
            collection_id=orm.collection_id,
        )

    def is_adult_only(self) -> bool:
        return self.age_rating == AgeRating.ADULT

    def has_platform(self, provider: str) -> bool:
        return any(p.provider == provider for p in self.platforms)

    def platform_providers(self) -> list[str]:
        return [p.provider for p in self.platforms]


if __name__ == "__main__":
    from types import SimpleNamespace

    mock_orm = SimpleNamespace(
        id=1,
        slug="interstellar",
        title="인터스텔라",
        release_year="2014",
        rating=4.8,
        poster_url="https://example.com/poster.jpg",
        platforms=[{"provider": "netflix", "url": None, "type": "subscription"}],
        age_rating="12세",
        genres=["SF", "드라마"],
        collection_id=None,
    )
    movie = MovieEntity.from_orm(mock_orm)
    assert movie.slug == "interstellar"
    assert movie.age_rating == AgeRating.TWELVE
    assert not movie.is_adult_only()
    assert movie.has_platform("netflix")
    assert movie.platform_providers() == ["netflix"]
    print("studio_movies_entity OK")
