"""미니게임 PgRepository — 랜덤 표본, 초성 계산, 스코어·리더보드."""

from __future__ import annotations

import logging

from sqlalchemy import Integer, and_, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_game_scores_orm import MovaGameScore
from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.games_dto import (
    ChosungQuestionDto,
    LeaderboardDto,
    LeaderboardEntryDto,
    MemoryDeckDto,
    MemoryDeckPairDto,
    ScoreSaveCommand,
)
from mova.app.ports.output.games_repository import GamesRepositoryPort
from viewer.adapter.outbound.orm.user_orm import get_viewer_user_nicknames

logger = logging.getLogger(__name__)

_CHOSUNG_LIST = (
    "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
)


def _to_chosung_spaced(text: str) -> str:
    """원래 형태 유지, 한글 음절은 초성으로 대체."""
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            out.append(_CHOSUNG_LIST[(code - 0xAC00) // 588])
        else:
            out.append(ch)
    return "".join(out)


def _to_chosung_condensed(text: str) -> str:
    """공백·구두점 제거, 한글은 초성만, 영숫자는 대문자 유지."""
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            out.append(_CHOSUNG_LIST[(code - 0xAC00) // 588])
        elif ch.isalnum():
            out.append(ch.upper())
    return "".join(out)


def _is_korean_movie(movie: MovaMovie) -> bool:
    """origin_country에 KR이 있거나 original_language가 ko면 한국영화."""
    countries = movie.origin_country or []
    if isinstance(countries, list) and "KR" in countries:
        return True
    if movie.original_language == "ko":
        return True
    return False


def _pool_conditions(min_rating: float):
    """미니게임 영화 풀 필터.

    - rating >= min_rating (2.5 기본)
    - 한글 문자 최소 1자 포함(라틴 전용 제목 배제: "VIZIOEPROVOCAZIONE" 등)
    - age_rating 있음(TMDB KR release_dates.certification 백필 대상 = 한국 상영이력)
    - poster/title 비어있지 않음

    2026-08-13 사용자 피드백: 완전 라틴 제목·미상영 마이너 외국영화가 노출돼
    난이도가 비합리적으로 높다는 지적. 한국 상영작으로 좁혀 실전 난이도로 맞춤.
    실측(EC2): 필터 통과 편수 1517편.
    """
    return [
        MovaMovie.rating >= min_rating,
        MovaMovie.poster_url != "",
        MovaMovie.title != "",
        MovaMovie.title.op("~")("[가-힣]"),
        MovaMovie.age_rating.isnot(None),
    ]


class GamesPgRepository(GamesRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sample_chosung_question(self, min_rating: float) -> ChosungQuestionDto | None:
        row = (
            await self._session.execute(
                select(MovaMovie)
                .where(*_pool_conditions(min_rating))
                .order_by(func.random())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return None

        cast_rows = (
            await self._session.execute(
                select(MovaActor.name)
                .join(MovaCharacter, MovaCharacter.actor_id == MovaActor.id)
                .where(MovaCharacter.movie_id == row.id)
                .order_by(MovaCharacter.billing_order.asc().nullslast())
                .limit(5)
            )
        ).scalars().all()

        return ChosungQuestionDto(
            movie_id=row.id,
            title=row.title,
            chosung_condensed=_to_chosung_condensed(row.title),
            chosung_spaced=_to_chosung_spaced(row.title),
            is_korean=_is_korean_movie(row),
            cast_names=list(cast_rows),
            poster_url=row.poster_url,
        )

    async def sample_memory_deck(self, stage: int, min_rating: float) -> MemoryDeckDto:
        pairs_needed = 2 * stage
        rows = (
            await self._session.execute(
                select(MovaMovie)
                .where(*_pool_conditions(min_rating))
                .order_by(func.random())
                .limit(pairs_needed)
            )
        ).scalars().all()

        return MemoryDeckDto(
            stage=stage,
            pairs=[
                MemoryDeckPairDto(movie_id=m.id, title=m.title, poster_url=m.poster_url)
                for m in rows
            ],
        )

    async def save_score(self, command: ScoreSaveCommand) -> None:
        self._session.add(
            MovaGameScore(
                user_id=command.user_id,
                game_type=command.game_type,
                stage=command.stage,
                score=command.score,
                hints_used=command.hints_used,
            )
        )
        await self._session.commit()

    async def leaderboard(
        self, *, game_type: str, stage: int | None, limit: int, me_user_id: int | None
    ) -> LeaderboardDto:
        # 각 유저의 "최고 기록"만 뽑는다 — 같은 유저의 여러 시도 중 상위 1건.
        # chosung: score DESC, hints_used ASC, played_at ASC (=먼저 낸 사람 우선)
        # memory : score ASC (=빠를수록 좋음), played_at ASC
        if game_type == "chosung":
            order_partition = (
                MovaGameScore.score.desc(),
                MovaGameScore.hints_used.asc(),
                MovaGameScore.played_at.asc(),
            )
        else:  # memory
            order_partition = (
                MovaGameScore.score.asc(),
                MovaGameScore.played_at.asc(),
            )

        row_number = (
            func.row_number()
            .over(
                partition_by=MovaGameScore.user_id,
                order_by=order_partition,
            )
            .label("rn")
        )

        base_where = [MovaGameScore.game_type == game_type]
        if game_type == "memory":
            base_where.append(MovaGameScore.stage == stage)

        best_subq = (
            select(
                MovaGameScore.id,
                MovaGameScore.user_id,
                MovaGameScore.score,
                MovaGameScore.hints_used,
                MovaGameScore.played_at,
                row_number,
            )
            .where(and_(*base_where))
            .subquery()
        )

        # 전체 랭킹 매기기 — 유저 최고 기록만(rn=1) 대상으로 다시 order.
        if game_type == "chosung":
            overall_order = (
                desc(best_subq.c.score),
                best_subq.c.hints_used.asc(),
                best_subq.c.played_at.asc(),
            )
        else:
            overall_order = (
                best_subq.c.score.asc(),
                best_subq.c.played_at.asc(),
            )

        overall_rank = (
            func.row_number().over(order_by=overall_order).label("overall_rank")
        )
        ranked = (
            select(
                best_subq.c.user_id,
                best_subq.c.score,
                best_subq.c.hints_used,
                best_subq.c.played_at,
                overall_rank,
            )
            .where(best_subq.c.rn == 1)
            .subquery()
        )

        top_rows = (
            await self._session.execute(
                select(
                    ranked.c.user_id,
                    ranked.c.score,
                    ranked.c.hints_used,
                    ranked.c.played_at,
                    ranked.c.overall_rank,
                )
                .order_by(ranked.c.overall_rank.asc())
                .limit(limit)
            )
        ).all()

        me_row = None
        if me_user_id is not None:
            me_row = (
                await self._session.execute(
                    select(
                        ranked.c.user_id,
                        ranked.c.score,
                        ranked.c.hints_used,
                        ranked.c.played_at,
                        ranked.c.overall_rank,
                    )
                    .where(ranked.c.user_id == me_user_id)
                    .limit(1)
                )
            ).one_or_none()

        user_ids = {int(r.user_id) for r in top_rows}
        if me_row is not None:
            user_ids.add(int(me_row.user_id))
        nicknames = await get_viewer_user_nicknames(user_ids)

        def _mk(r) -> LeaderboardEntryDto:
            return LeaderboardEntryDto(
                rank=int(r.overall_rank),
                user_id=int(r.user_id),
                nickname=nicknames.get(int(r.user_id), ""),
                score=int(r.score),
                hints_used=int(r.hints_used),
                played_at=r.played_at,
            )

        return LeaderboardDto(
            game_type=game_type,
            stage=stage,
            top=[_mk(r) for r in top_rows],
            me=_mk(me_row) if me_row is not None else None,
        )


# `cast`·`Integer` import는 향후 partition rank 계산 확장 여지로 남긴다.
_ = cast
_ = Integer
