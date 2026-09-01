"""rating=5.0 소수평가 노이즈 완화 — 베이지안 가중 평점 SQL 표현식.

weighted = (v·R + m·C) / (v + m)
- v = movies.vote_count (TMDB, 0=미수집), R = movies.rating
- m = 신뢰 기준 투표 수, C = 전역 prior 평점

투표가 적은 영화는 C(3.0)로 수렴해 "1명이 10점 → rating 5.0" 노이즈가
상위 정렬을 오염시키지 못한다. vote_count 미수집(0)인 영화도 C로 수렴 —
KOFIC 단독 인입작 등이 과대평가되지 않는 안전한 기본값.
"""

from __future__ import annotations

from typing import Any

from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie

_M = 50  # 이 정도 투표는 쌓여야 rating을 액면 그대로 신뢰
_PRIOR = 3.0  # 전역 prior (0.5~5.0 스케일 중간값 근사)


def weighted_rating_expr() -> Any:
    """ORDER BY용 가중 평점 식 — 높을수록 좋음(desc 정렬에 사용)."""
    v = MovaMovie.vote_count
    return (v * MovaMovie.rating + _M * _PRIOR) / (v + _M)
