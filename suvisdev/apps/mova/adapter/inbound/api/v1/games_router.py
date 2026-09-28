"""미니게임(초성·카드 뒤집기) 라우터.

- GET  /mova/games/chosung/next          — 랜덤 문제 1개(정답 포함, 게임이라 감수)
- GET  /mova/games/memory/deck?stage=N   — N단계 카드 세트(2N쌍)
- POST /mova/games/scores                — 점수 저장(로그인 필수)
- GET  /mova/games/leaderboard?...       — 리더보드(로그인 없어도 조회 가능, me만 익명이면 null)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from shared.security.require_user import UserPrincipal, optional_user, require_user

from mova.adapter.inbound.api.schemas.games_schema import (
    ChosungQuestionSchema,
    LeaderboardSchema,
    MemoryDeckSchema,
    ScoreSaveSchema,
)
from mova.app.ports.input.games_use_case import GamesUseCase
from mova.app.ports.output.games_errors import GamesError
from mova.dependencies.games_provider import get_games_use_case

games_router = APIRouter(prefix="/games", tags=["mova-games"])


def _http(e: GamesError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


@games_router.get("/chosung/next", response_model=ChosungQuestionSchema)
async def next_chosung_question(
    category: str = Query("all", pattern="^(all|kr|foreign)$"),
    exclude: str = Query("", description="쉼표 구분 movie_id — 이번 게임 세션 중 배제"),
    use_case: GamesUseCase = Depends(get_games_use_case),
) -> ChosungQuestionSchema:
    exclude_ids: list[int] = []
    for tok in exclude.split(","):
        tok = tok.strip()
        if tok.isdigit():
            exclude_ids.append(int(tok))
    try:
        return (await use_case.next_chosung_question(category, exclude_ids)).to_schema()
    except GamesError as e:
        raise _http(e) from e


@games_router.get("/memory/deck", response_model=MemoryDeckSchema)
async def memory_deck(
    stage: int = Query(..., ge=1, le=10),
    use_case: GamesUseCase = Depends(get_games_use_case),
) -> MemoryDeckSchema:
    try:
        return (await use_case.memory_deck(stage)).to_schema()
    except GamesError as e:
        raise _http(e) from e


@games_router.post("/scores", status_code=201)
async def save_score(
    payload: ScoreSaveSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: GamesUseCase = Depends(get_games_use_case),
) -> dict[str, str]:
    try:
        await use_case.save_score(principal.user_id, payload)
    except GamesError as e:
        raise _http(e) from e
    return {"status": "saved"}


@games_router.get("/leaderboard", response_model=LeaderboardSchema)
async def leaderboard(
    game: str = Query(..., pattern="^(chosung|memory)$"),
    stage: int | None = Query(default=None, ge=1, le=10),
    limit: int = Query(default=10, ge=1, le=50),
    principal: UserPrincipal | None = Depends(optional_user),
    use_case: GamesUseCase = Depends(get_games_use_case),
) -> LeaderboardSchema:
    me_user_id = principal.user_id if principal else None
    try:
        dto = await use_case.leaderboard(
            game_type=game, stage=stage, limit=limit, me_user_id=me_user_id
        )
    except GamesError as e:
        raise _http(e) from e
    return dto.to_schema()
