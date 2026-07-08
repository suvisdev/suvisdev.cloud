"""picks 도메인 Value Objects — 추천 순위·피드백."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# 배치(한 번의 AI 응답) 안 추천 순위 범위
PICK_RANK_MIN = 1
PICK_RANK_MAX = 3


@dataclass(frozen=True)
class PickRank:
    """AI 추천 배치 내 순위. 1~3만 허용 (불변·자기검증)."""

    value: int

    def __post_init__(self) -> None:
        if not PICK_RANK_MIN <= self.value <= PICK_RANK_MAX:
            raise ValueError(f"PickRank must be {PICK_RANK_MIN}..{PICK_RANK_MAX}, got {self.value}")

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    @property
    def is_top(self) -> bool:
        """배치 1순위 여부."""
        return self.value == PICK_RANK_MIN


class Feedback(str, Enum):
    """추천 자체에 대한 사용자 반응. 미반응(null)은 None으로 표현한다."""

    LIKE = "like"
    DISLIKE = "dislike"

    @classmethod
    def from_str(cls, value: str | None) -> Feedback | None:
        """원시 문자열 → Feedback. 공백 정리·소문자화 후 매칭, 무효·빈값은 None."""
        if not value:
            return None
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        return None


if __name__ == "__main__":
    assert PickRank(1).is_top
    assert not PickRank(2).is_top
    assert int(PickRank(3)) == 3
    for bad in (0, 4):
        try:
            PickRank(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"PickRank({bad}) should raise")

    assert Feedback.from_str("LIKE ") is Feedback.LIKE
    assert Feedback.from_str("dislike") is Feedback.DISLIKE
    assert Feedback.from_str(None) is None
    assert Feedback.from_str("") is None
    assert Feedback.from_str("meh") is None

    print("market_picks_vo OK")
