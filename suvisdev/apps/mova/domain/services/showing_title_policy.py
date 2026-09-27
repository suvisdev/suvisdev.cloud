"""동명 작품 중 어느 해 작품을 고를지 — 예매 트랙의 도메인 규칙(2026-09-27).

"인턴 예매"에 2015년작이 나간 사고(WORK_LOG_MOVA 09-27): 카탈로그 정렬은 평점 우선이라 옛
작품을 앞세운다. 예매 문맥에선 **지금 상영 중인 쪽**이 정답이고, 상영 여부는 박스오피스
개봉 연도로 판정한다. 개봉 연도를 모르면 최신작.
"""

from __future__ import annotations

from collections.abc import Iterable


def _year_of(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


def prefer_showing_year(candidate_years: Iterable[str | None], open_years: set[int]) -> str | None:
    """후보 연도들 중 박스오피스 개봉 연도와 맞는 것, 없으면 가장 최신 연도. 후보가 없으면 None."""
    years = [y for y in candidate_years if _year_of(y) is not None]
    if not years:
        return None
    matched = [y for y in years if _year_of(y) in open_years]
    if matched:
        return matched[0]
    return max(years, key=lambda y: _year_of(y) or 0)
