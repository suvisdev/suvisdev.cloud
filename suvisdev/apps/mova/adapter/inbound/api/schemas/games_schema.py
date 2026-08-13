"""미니게임(초성·카드 뒤집기) 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChosungQuestionSchema(BaseModel):
    """초성 게임 한 문제. 정답(title)은 클라이언트 검증용 — 개발자 도구로
    노출되지만 게임 몰입 이슈 정도라 감수."""

    movie_id: int
    title: str
    chosung_condensed: str  # 힌트 사용 전: 공백·구두점 제거, 한글은 초성만
    chosung_spaced: str  # 힌트1: 원래 형태 유지, 한글만 초성으로 대체
    is_korean: bool  # 힌트1의 (한국영화/외국영화) 태그
    cast_names: list[str]  # 힌트2: 상위 5명까지
    poster_url: str  # 힌트3: 프론트에서 CSS로 1/4만 노출


class MemoryDeckPairSchema(BaseModel):
    movie_id: int
    title: str
    poster_url: str


class MemoryDeckSchema(BaseModel):
    stage: int
    pairs: list[MemoryDeckPairSchema]  # 2*stage 개


GameType = Literal["chosung", "memory"]


class ScoreSaveSchema(BaseModel):
    game_type: GameType
    stage: int | None = None  # memory만 필수
    score: int = Field(ge=0)
    hints_used: int = Field(ge=0, default=0)


class LeaderboardEntrySchema(BaseModel):
    rank: int
    user_id: int
    nickname: str
    score: int
    hints_used: int
    played_at: datetime
    # memory 통합 리더보드용. chosung은 stage=None.
    # computed_score = 실제 정렬 기준(memory: stage*1000+GREATEST(0,500-elapsed), chosung: score 그대로)
    stage: int | None = None
    computed_score: int = 0


class LeaderboardSchema(BaseModel):
    game_type: GameType
    stage: int | None
    top: list[LeaderboardEntrySchema]
    me: LeaderboardEntrySchema | None
