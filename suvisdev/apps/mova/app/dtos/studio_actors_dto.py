"""배우/감독 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MovieInActorDto:
    """배우 filmography 항목 — characters + movies JOIN 결과."""

    character_id: int
    movie_id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    genres: list[str]


@dataclass(frozen=True)
class ActorDetailDto:
    """배우/감독 상세 + 출연작 목록."""

    id: int
    name: str
    role_type: str
    profile_photo_url: str
    filmography: list[MovieInActorDto]

    @classmethod
    def from_orm(cls, actor: object, movie_rows: list) -> ActorDetailDto:
        filmography = [
            MovieInActorDto(
                character_id=char.id,
                movie_id=movie.id,
                slug=movie.slug,
                title=movie.title,
                release_year=movie.release_year or "",
                rating=movie.rating or 0.0,
                poster_url=movie.poster_url or "",
                genres=list(movie.genres or []),
            )
            for char, movie in movie_rows
        ]
        return cls(
            id=actor.id,
            name=actor.name,
            role_type=actor.role_type or "actor",
            profile_photo_url=actor.profile_photo_url or "",
            filmography=filmography,
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_actors_schema import (
            ActorDetailSchema,
            MovieInActorSchema,
        )

        return ActorDetailSchema(
            id=self.id,
            name=self.name,
            role_type=self.role_type,
            profile_photo_url=self.profile_photo_url,
            filmography=[
                MovieInActorSchema(
                    character_id=f.character_id,
                    movie_id=f.movie_id,
                    slug=f.slug,
                    title=f.title,
                    release_year=f.release_year,
                    rating=f.rating,
                    poster_url=f.poster_url,
                    genres=f.genres,
                )
                for f in self.filmography
            ],
        )


if __name__ == "__main__":
    from types import SimpleNamespace

    mock_actor = SimpleNamespace(id=1, name="전지현", role_type="actor", profile_photo_url="")
    mock_char = SimpleNamespace(id=10)
    mock_movie = SimpleNamespace(
        id=5,
        slug="assassination",
        title="암살",
        release_year="2015",
        rating=4.2,
        poster_url="",
        genres=["액션"],
    )
    dto = ActorDetailDto.from_orm(mock_actor, [(mock_char, mock_movie)])
    assert dto.name == "전지현"
    assert len(dto.filmography) == 1
    assert dto.filmography[0].slug == "assassination"
    print("studio_actors_dto OK")
