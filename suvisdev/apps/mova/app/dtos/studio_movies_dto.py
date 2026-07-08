"""영화 DTO — 앱 레이어와 HTTP 레이어를 분리한다."""

from __future__ import annotations

from dataclasses import dataclass

# ── 중첩 DTO ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlatformDto:
    provider: str
    url: str | None
    type: str | None

    @classmethod
    def from_dict(cls, d: dict) -> PlatformDto:
        return cls(provider=d.get("provider", ""), url=d.get("url"), type=d.get("type"))


@dataclass(frozen=True)
class ActorInMovieDto:
    """characters + actors JOIN 결과 — 출연진 한 줄."""

    character_id: int
    actor_id: int
    name: str
    role_type: str
    profile_photo_url: str


@dataclass(frozen=True)
class TagInMovieDto:
    """tags 테이블 한 줄."""

    id: int
    tag_kind: str
    slug: str
    label: str
    description: str
    character_id: int | None


# ── 상세 DTO (GET /movies/{slug}) ────────────────────────────────────────────


@dataclass(frozen=True)
class MovieDetailDto:
    id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    platforms: list[PlatformDto]
    age_rating: str | None
    genres: list[str]
    collection_id: int | None
    actors: list[ActorInMovieDto]
    tags: list[TagInMovieDto]

    @classmethod
    def from_orm(
        cls,
        movie: object,
        char_actor_rows: list,
        tag_rows: list,
    ) -> MovieDetailDto:
        platforms = [
            PlatformDto.from_dict(p)
            if isinstance(p, dict)
            else PlatformDto(p.provider, p.url, p.type)
            for p in (getattr(movie, "platforms", None) or [])
        ]
        actors = [
            ActorInMovieDto(
                character_id=char.id,
                actor_id=actor.id,
                name=actor.name,
                role_type=actor.role_type,
                profile_photo_url=actor.profile_photo_url or "",
            )
            for char, actor in char_actor_rows
        ]
        tags = [
            TagInMovieDto(
                id=t.id,
                tag_kind=t.tag_kind,
                slug=t.slug,
                label=t.label,
                description=t.description or "",
                character_id=t.character_id,
            )
            for t in tag_rows
        ]
        return cls(
            id=movie.id,
            slug=movie.slug,
            title=movie.title,
            release_year=movie.release_year or "",
            rating=movie.rating or 0.0,
            poster_url=movie.poster_url or "",
            platforms=platforms,
            age_rating=movie.age_rating,
            genres=list(movie.genres or []),
            collection_id=movie.collection_id,
            actors=actors,
            tags=tags,
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_movies_schema import (
            ActorInMovieSchema,
            MovieDetailSchema,
            PlatformSchema,
            TagInMovieSchema,
        )

        return MovieDetailSchema(
            id=self.id,
            slug=self.slug,
            title=self.title,
            release_year=self.release_year,
            rating=self.rating,
            poster_url=self.poster_url,
            platforms=[
                PlatformSchema(provider=p.provider, url=p.url, type=p.type) for p in self.platforms
            ],
            age_rating=self.age_rating,
            genres=self.genres,
            collection_id=self.collection_id,
            actors=[
                ActorInMovieSchema(
                    character_id=a.character_id,
                    actor_id=a.actor_id,
                    name=a.name,
                    role_type=a.role_type,
                    profile_photo_url=a.profile_photo_url,
                )
                for a in self.actors
            ],
            tags=[
                TagInMovieSchema(
                    id=t.id,
                    tag_kind=t.tag_kind,
                    slug=t.slug,
                    label=t.label,
                    description=t.description,
                    character_id=t.character_id,
                )
                for t in self.tags
            ],
        )


# ── 목록 DTO (GET /movies) ───────────────────────────────────────────────────


@dataclass(frozen=True)
class MovieListItemDto:
    id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    platforms: list[PlatformDto]
    age_rating: str | None
    genres: list[str]

    @classmethod
    def from_orm(cls, movie: object) -> MovieListItemDto:
        platforms = [
            PlatformDto.from_dict(p)
            if isinstance(p, dict)
            else PlatformDto(p.provider, p.url, p.type)
            for p in (getattr(movie, "platforms", None) or [])
        ]
        return cls(
            id=movie.id,
            slug=movie.slug,
            title=movie.title,
            release_year=movie.release_year or "",
            rating=movie.rating or 0.0,
            poster_url=movie.poster_url or "",
            platforms=platforms,
            age_rating=movie.age_rating,
            genres=list(movie.genres or []),
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_movies_schema import (
            MovieListItemSchema,
            PlatformSchema,
        )

        return MovieListItemSchema(
            id=self.id,
            slug=self.slug,
            title=self.title,
            release_year=self.release_year,
            rating=self.rating,
            poster_url=self.poster_url,
            platforms=[
                PlatformSchema(provider=p.provider, url=p.url, type=p.type) for p in self.platforms
            ],
            age_rating=self.age_rating,
            genres=self.genres,
        )


@dataclass(frozen=True)
class MovieListDto:
    items: list[MovieListItemDto]
    total: int
    limit: int
    offset: int

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_movies_schema import MovieListSchema

        return MovieListSchema(
            items=[item.to_schema() for item in self.items],
            total=self.total,
            limit=self.limit,
            offset=self.offset,
        )


# ── 필터 쿼리 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MovieFilterQuery:
    genre: str | None = None
    release_year: str | None = None
    min_rating: float | None = None
    age_rating: str | None = None
    platform: str | None = None
    sort: str = "latest"
    limit: int = 20
    offset: int = 0


if __name__ == "__main__":
    from types import SimpleNamespace

    mock = SimpleNamespace(
        id=1,
        slug="interstellar",
        title="인터스텔라",
        release_year="2014",
        rating=4.8,
        poster_url="",
        platforms=[{"provider": "netflix", "url": None, "type": None}],
        age_rating="12세",
        genres=["SF"],
        collection_id=None,
    )
    dto = MovieListItemDto.from_orm(mock)
    assert dto.slug == "interstellar"
    assert dto.platforms[0].provider == "netflix"
    print("studio_movies_dto OK")
