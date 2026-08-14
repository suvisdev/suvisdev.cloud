"""미니게임 PgRepository — 랜덤 표본, 초성 계산, 스코어·리더보드."""

from __future__ import annotations

import logging

from sqlalchemy import Integer, and_, cast, desc, func, or_, select
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

# 한자음 숫자 초성. 0=영(ㅇ), 1=일(ㅇ), 2=이(ㅇ), 3=삼(ㅅ), 4=사(ㅅ),
# 5=오(ㅇ), 6=육(ㅇ), 7=칠(ㅊ), 8=팔(ㅍ), 9=구(ㄱ). "20세기 소년"이
# 사용자에겐 "이십세기소년"이라 초성 "ㅇㅅㅅㄱㅅㄴ"이어야 자연스러움
# (2026-08-13 사용자 지적). "20"→"이십"→"ㅇㅅ" 처럼 자리수 단위(십/백/천/만)
# 를 함께 발음으로 풀어낸다.
_DIGIT_TO_CHO = "ㅇㅇㅇㅅㅅㅇㅇㅊㅍㄱ"

# 시리즈 넘버(공백 뒤 짧은 정수) 전용 영어 발음 초성. 한글 발음 그대로
# 음절별 초성을 이어붙인다 — "3(쓰리)" → 쓰·리 → ㅆㄹ, "5(파이브)" →
# 파·이·브 → ㅍㅇㅂ. "강철비 2: 정상회담" → "강철비 투" → "ㄱㅊㅂㅌ"
# (2026-08-14 사용자 지적: 한자음 "이"보다 영어 "투"가 시리즈 표기 관용).
_SERIES_DIGIT_TO_CHO = {
    1: "ㅇ",     # 원
    2: "ㅌ",     # 투
    3: "ㅆㄹ",   # 쓰리
    4: "ㅍ",     # 포
    5: "ㅍㅇㅂ", # 파이브
    6: "ㅅㅅ",   # 식스
    7: "ㅅㅂ",   # 세븐
    8: "ㅇㅇ",   # 에잇
    9: "ㄴㅇ",   # 나인
    10: "ㅌ",    # 텐
}


def _integer_to_chosung(n: int) -> str:
    """자연수를 한자음(이십, 백, 천) 기준 초성으로. 만 이상은 만 단위로 재귀."""
    if n == 0:
        return "ㅇ"
    if n < 0:
        n = -n
    out: list[str] = []
    if n >= 10000:
        out.append(_integer_to_chosung(n // 10000))
        out.append("ㅁ")
        n %= 10000
    if n >= 1000:
        t = n // 1000
        if t > 1:
            out.append(_DIGIT_TO_CHO[t])
        out.append("ㅊ")
        n %= 1000
    if n >= 100:
        b = n // 100
        if b > 1:
            out.append(_DIGIT_TO_CHO[b])
        out.append("ㅂ")
        n %= 100
    if n >= 10:
        s = n // 10
        if s > 1:
            out.append(_DIGIT_TO_CHO[s])
        out.append("ㅅ")
        n %= 10
    if n > 0:
        out.append(_DIGIT_TO_CHO[n])
    return "".join(out)


def _replace_digit_runs(text: str) -> str:
    """숫자 뭉치를 초성으로 치환. 앞에 공백이 있고 값이 1~10인 짧은 정수는
    시리즈 넘버로 간주 → 영어 발음("투"·"쓰리"), 그 외는 한자음("이십"·"삼")."""
    import re

    def _repl(m: re.Match[str]) -> str:
        s = m.group(0)
        n = int(s)
        prev = text[m.start() - 1] if m.start() > 0 else ""
        if prev == " " and n in _SERIES_DIGIT_TO_CHO:
            return _SERIES_DIGIT_TO_CHO[n]
        return _integer_to_chosung(n)

    return re.sub(r"\d+", _repl, text)


def _to_chosung_spaced(text: str) -> str:
    """원래 형태 유지, 한글 음절·숫자 뭉치는 한자음 초성으로 대체."""
    replaced = _replace_digit_runs(text)
    out: list[str] = []
    for ch in replaced:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            out.append(_CHOSUNG_LIST[(code - 0xAC00) // 588])
        else:
            out.append(ch)
    return "".join(out)


def _to_chosung_condensed(text: str) -> str:
    """공백·구두점 제거, 한글은 초성만, 숫자 뭉치는 한자음 초성, 영문은 대문자."""
    replaced = _replace_digit_runs(text)
    out: list[str] = []
    for ch in replaced:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            out.append(_CHOSUNG_LIST[(code - 0xAC00) // 588])
        elif ch.isalpha():
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


def _common_conditions():
    """모든 게임 풀 공통: title/poster 있음, 한글 포함, 시리즈 후속편 배제,
    청소년 관람불가(청불) 등급 제외. "청불"만 뽑으면 성인/에로 영화가
    게임 풀에 섞여 나오는 문제(2026-08-14 사용자 지적: "유부녀의 사정일지"
    등)를 원천 차단.
    """
    return [
        MovaMovie.poster_url != "",
        MovaMovie.title != "",
        MovaMovie.title.op("~")("[가-힣]"),
        MovaMovie.title.op("!~")(" [0-9]+$"),
        (MovaMovie.age_rating != "청불") | (MovaMovie.age_rating.is_(None)),
    ]


def _kr_pool_conditions(min_rating: float):
    """한국 영화 풀. age_rating/platforms 필터 제외 — TMDB가 한국 영화에 이
    두 필드를 대체로 안 채워주기 때문(실측 2026-08-13: KR 게임 풀 1919 → 29 →
    20편으로 축소됨). rating cap 2.5→3.3 상향(2026-08-14 사용자 지적:
    "여교사: 제자와의 사랑" rating 2.9가 초성 게임에 노출됨). TMDB `adult`
    플래그·KR 청불 등급이 없어도 rating 3.3 미만은 저품질·성인 오탐이 많아
    일괄 배제. 3.3 컷 시 KR 풀 707편(2.5 컷 1279 → 3.3 컷 707) — 게임
    다양성엔 충분. 청불 배제는 `_common_conditions()`에서 처리.
    """
    return [
        *_common_conditions(),
        MovaMovie.rating >= min(min_rating, 3.3),
        MovaMovie.original_language == "ko",
    ]


def _foreign_pool_conditions(min_rating: float):
    """외국 영화 풀. 사용자 지시(2026-08-13): "유명하고 인기 있는 영화만".
    엄격 필터 유지 — rating 3.0+ · age_rating 있음(KR 심의 통과) · KR OTT
    플랫폼 하나 이상. 한국 영화(original_language='ko') 제외. 청불 배제는
    _common_conditions()에서 처리.
    """
    return [
        *_common_conditions(),
        MovaMovie.rating >= min_rating,
        (MovaMovie.original_language != "ko") | (MovaMovie.original_language.is_(None)),
        MovaMovie.age_rating.isnot(None),
        func.jsonb_array_length(MovaMovie.platforms) > 0,
    ]


# 2026-08-13 이전 단일 필터. 남겨두면 다른 곳(카드 뒤집기)이 여전히 참조.
# 여기서는 두 풀의 합집합 개념으로 유지 — 카드 뒤집기는 category 개념 없으므로
# 기존 엄격 조건(외국) 그대로 쓰되 한국 영화도 원산지·평점 낮은 것까지 포함.
def _pool_conditions(min_rating: float):
    """카드 뒤집기·기타 용도의 통합 풀 — KR 완화 조건과 외국 엄격 조건의 합집합.

    카드 뒤집기는 카테고리 개념이 없어 두 풀을 OR로 합쳐 다양성 확보.
    """
    common = _common_conditions()
    kr_branch = and_(
        MovaMovie.rating >= min(min_rating, 3.3),
        MovaMovie.original_language == "ko",
    )
    foreign_branch = and_(
        MovaMovie.rating >= min_rating,
        (MovaMovie.original_language != "ko") | (MovaMovie.original_language.is_(None)),
        MovaMovie.age_rating.isnot(None),
        func.jsonb_array_length(MovaMovie.platforms) > 0,
    )
    return [*common, or_(kr_branch, foreign_branch)]


class GamesPgRepository(GamesRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sample_chosung_question(
        self,
        min_rating: float,
        *,
        category: str = "all",
        exclude_ids: list[int] | None = None,
    ) -> ChosungQuestionDto | None:
        import random as _random

        exclude_ids = exclude_ids or []

        async def _try(conds: list) -> MovaMovie | None:
            all_conds = list(conds)
            if exclude_ids:
                all_conds.append(MovaMovie.id.notin_(exclude_ids))
            return (
                await self._session.execute(
                    select(MovaMovie).where(*all_conds).order_by(func.random()).limit(1)
                )
            ).scalar_one_or_none()

        # 카테고리별 후보 풀 선정. 'all'은 70% 한국 · 30% 외국(사용자 지시
        # 2026-08-13). 선택된 풀에서 소진 시 반대 풀로 폴백.
        if category == "kr":
            row = await _try(_kr_pool_conditions(min_rating))
        elif category == "foreign":
            row = await _try(_foreign_pool_conditions(min_rating))
        else:
            prefer_kr = _random.random() < 0.7
            first = _kr_pool_conditions(min_rating) if prefer_kr else _foreign_pool_conditions(min_rating)
            second = _foreign_pool_conditions(min_rating) if prefer_kr else _kr_pool_conditions(min_rating)
            row = await _try(first) or await _try(second)
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
