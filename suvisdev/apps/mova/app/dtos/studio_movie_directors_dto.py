"""영화↔감독 연결 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MovieDirectorUpsertCommand:
    """(movie_id, actor_id) 기준 upsert — 공동 감독 허용."""

    movie_id: int
    actor_id: int
