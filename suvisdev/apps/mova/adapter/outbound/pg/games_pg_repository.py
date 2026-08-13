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
    - 시리즈 후속편(제목 끝이 " 숫자") 배제: "슈렉 2/3/5", "존 윅 4", "토이 스토리 3" 등
      → 시리즈는 원작(숫자 없는 편)만 문제로 남는다. TMDB collection_id는 실측
      결과 0.3%만 채워져 있어(2026-08-13) 컬렉션 기반 필터는 무용지물.
      정규식 " [0-9]+$" — 원작 부제(007 스카이폴, 쓰리 빌보드 등)는 오탐 없음.

    2026-08-13 사용자 피드백: 완전 라틴 제목·미상영 마이너 외국영화가 노출돼
    난이도가 비합리적으로 높고, "슈렉 3 → ㅅㄹ3"처럼 후속편 번호가 초성게임
    본질을 해치는 문제. 한국 상영작 + 원작만 남기게 좁힘.
    실측(EC2): 필터 통과 편수 1517 → 1383편.
    """
    return [
        MovaMovie.rating >= min_rating,
        MovaMovie.poster_url != "",
        MovaMovie.title != "",
        MovaMovie.title.op("~")("[가-힣]"),
        MovaMovie.title.op("!~")(" [0-9]+$"),
        MovaMovie.age_rating.isnot(None),
        # KR OTT 플랫폼(넷플릭스/티빙/왓챠 등) 하나 이상 있음 = 실제 국내 접근
        # 가능한 영화. age_rating만으론 심의만 받고 실제 상영 없는 마이너 외국영화
        # (태국·인도 등)가 통과함(2026-08-13 사용자 재지적).
        func.jsonb_array_length(MovaMovie.platforms) > 0,
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
        # chosung: score DESC(맞춘 개수), hints_used ASC, played_at ASC
        # memory : 통합 formula = stage * 1000 + GREATEST(0, 500 - elapsed_seconds)
        #          제약 1) 1단계 최대(1500) < 10단계 최소(10000) — 단계 대역 분리
        #          제약 2) 같은 단계 20초 차이 = 20점 차이 — 앞선 사람 무조건 상위
        #   stage 파라미터는 memory에서도 무시(통합 리더보드, 2026-08-13).
        if game_type == "chosung":
            metric = MovaGameScore.score
            metric_order = metric.desc()
            best_row_order = (
                metric.desc(),
                MovaGameScore.hints_used.asc(),
                MovaGameScore.played_at.asc(),
            )
        else:  # memory 통합
            metric = (
                MovaGameScore.stage * 1000
                + func.greatest(0, 500 - MovaGameScore.score)
            )
            metric_order = metric.desc()
            best_row_order = (metric_order, MovaGameScore.played_at.asc())

        row_number = (
            func.row_number()
            .over(
                partition_by=MovaGameScore.user_id,
                order_by=best_row_order,
            )
            .label("rn")
        )

        best_subq = (
            select(
                MovaGameScore.id,
                MovaGameScore.user_id,
                MovaGameScore.stage,
                MovaGameScore.score,
                MovaGameScore.hints_used,
                MovaGameScore.played_at,
                metric.label("metric"),
                row_number,
            )
            .where(MovaGameScore.game_type == game_type)
            .subquery()
        )

        # 전체 랭킹 매기기 — 유저 최고 기록만(rn=1) 대상으로 다시 order.
        if game_type == "chosung":
            overall_order = (
                desc(best_subq.c.metric),
                best_subq.c.hints_used.asc(),
                best_subq.c.played_at.asc(),
            )
        else:
            overall_order = (desc(best_subq.c.metric), best_subq.c.played_at.asc())

        overall_rank = (
            func.row_number().over(order_by=overall_order).label("overall_rank")
        )
        ranked = (
            select(
                best_subq.c.user_id,
                best_subq.c.stage,
                best_subq.c.score,
                best_subq.c.hints_used,
                best_subq.c.played_at,
                best_subq.c.metric,
                overall_rank,
            )
            .where(best_subq.c.rn == 1)
            .subquery()
        )

        top_rows = (
            await self._session.execute(
                select(
                    ranked.c.user_id,
                    ranked.c.stage,
                    ranked.c.score,
                    ranked.c.hints_used,
                    ranked.c.played_at,
                    ranked.c.metric,
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
                        ranked.c.stage,
                        ranked.c.score,
                        ranked.c.hints_used,
                        ranked.c.played_at,
                        ranked.c.metric,
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
                stage=int(r.stage) if r.stage is not None else None,
                computed_score=int(r.metric),
            )

        return LeaderboardDto(
            game_type=game_type,
            stage=None,  # 통합 리더보드 — memory도 stage 별도 필터 안 함
            top=[_mk(r) for r in top_rows],
            me=_mk(me_row) if me_row is not None else None,
        )


# `cast`·`Integer` import는 향후 partition rank 계산 확장 여지로 남긴다.
_ = cast
_ = Integer
