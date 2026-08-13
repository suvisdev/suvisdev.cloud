"""미니게임 DTO — 초성 게임 문제·카드 덱·스코어·리더보드."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChosungQuestionDto:
    movie_id: int
    title: str
    chosung_condensed: str
    chosung_spaced: str
    is_korean: bool
    cast_names: list[str]
    poster_url: str

    def to_schema(self):
        from mova.adapter.inbound.api.schemas.games_schema import ChosungQuestionSchema

        return ChosungQuestionSchema(
            movie_id=self.movie_id,
            title=self.title,
            chosung_condensed=self.chosung_condensed,
            chosung_spaced=self.chosung_spaced,
            is_korean=self.is_korean,
            cast_names=list(self.cast_names),
            poster_url=self.poster_url,
        )


@dataclass(frozen=True)
class MemoryDeckPairDto:
    movie_id: int
    title: str
    poster_url: str


@dataclass(frozen=True)
class MemoryDeckDto:
    stage: int
    pairs: list[MemoryDeckPairDto]

    def to_schema(self):
        from mova.adapter.inbound.api.schemas.games_schema import (
            MemoryDeckPairSchema,
            MemoryDeckSchema,
        )

        return MemoryDeckSchema(
            stage=self.stage,
            pairs=[
                MemoryDeckPairSchema(movie_id=p.movie_id, title=p.title, poster_url=p.poster_url)
                for p in self.pairs
            ],
        )


@dataclass(frozen=True)
class ScoreSaveCommand:
    user_id: int
    game_type: str  # 'chosung' | 'memory'
    stage: int | None
    score: int
    hints_used: int


@dataclass(frozen=True)
class LeaderboardEntryDto:
    rank: int
    user_id: int
    nickname: str
    score: int
    hints_used: int
    played_at: datetime
    # memory 통합 formula(2026-08-13) 노출용. chosung은 stage 없어서 None.
    # computed_score는 실제 정렬 기준: chosung은 맞춘 개수 그대로, memory는
    # stage*1000 + max(0, 500-elapsed).
    stage: int | None = None
    computed_score: int = 0


@dataclass(frozen=True)
class LeaderboardDto:
    game_type: str
    stage: int | None
    top: list[LeaderboardEntryDto]
    me: LeaderboardEntryDto | None

    def to_schema(self):
        from mova.adapter.inbound.api.schemas.games_schema import (
            LeaderboardEntrySchema,
            LeaderboardSchema,
        )

        def _entry(e: LeaderboardEntryDto) -> LeaderboardEntrySchema:
            return LeaderboardEntrySchema(
                rank=e.rank,
                user_id=e.user_id,
                nickname=e.nickname,
                score=e.score,
                hints_used=e.hints_used,
                played_at=e.played_at,
                stage=e.stage,
                computed_score=e.computed_score,
            )

        return LeaderboardSchema(
            game_type=self.game_type,  # type: ignore[arg-type]
            stage=self.stage,
            top=[_entry(e) for e in self.top],
            me=_entry(self.me) if self.me else None,
        )
