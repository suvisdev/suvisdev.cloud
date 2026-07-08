"""영화↔배우 연결 Value Objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterLink:
    """movies ↔ actors 연결의 비즈니스 키.

    (movie_id, actor_id) UNIQUE 제약을 도메인에서 표현한다.
    """

    movie_id: int
    actor_id: int

    def __post_init__(self) -> None:
        if self.movie_id <= 0:
            raise ValueError("movie_id must be positive")
        if self.actor_id <= 0:
            raise ValueError("actor_id must be positive")


if __name__ == "__main__":
    link = CharacterLink(movie_id=1, actor_id=2)
    assert link.movie_id == 1

    try:
        CharacterLink(movie_id=0, actor_id=1)
        assert False, "should raise"
    except ValueError:
        pass

    print("studio_characters_vo OK")
