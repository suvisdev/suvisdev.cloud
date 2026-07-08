from __future__ import annotations

from enum import Enum


class SeasonMode(Enum):
    """경로 가중치 계산 모드 값 객체.

    - SPRING_AUTUMN: 봄·가을 — 보너스 수종 가로수길 30% 감면.
    - WINTER_SAFETY: 겨울 — 결빙 사고 다발지역 근처 500% 증가.
    """

    SPRING_AUTUMN = "spring_autumn"
    WINTER_SAFETY = "winter_safety"

    @classmethod
    def from_value(cls, value: str) -> SeasonMode:
        """문자열을 모드 값 객체로 변환한다. 인식 불가 시 ValueError."""
        for mode in cls:
            if mode.value == value:
                return mode
        raise ValueError(f"알 수 없는 모드입니다: {value!r}")
