from __future__ import annotations

from enum import Enum

# 봄/가을 30% 감면 대상 수종 — 도메인 서비스의 가중치 규칙이 참조한다.
_BONUS_SPECIES = frozenset({"벚나무", "느티나무"})


class TreeSpecies(Enum):
    """가로수 수종 값 객체. 값은 data.go.kr 표준 데이터의 한글 표기를 그대로 쓴다."""

    CHERRY = "벚나무"
    ZELKOVA = "느티나무"
    GINKGO = "은행나무"

    @property
    def is_bonus_species(self) -> bool:
        """봄/가을 가중치 감면 대상(벚나무/느티나무) 여부."""
        return self.value in _BONUS_SPECIES

    @classmethod
    def from_label(cls, label: str) -> TreeSpecies:
        """한글 수종명을 값 객체로 변환한다. 인식 불가 시 ValueError."""
        normalized = label.strip()
        for species in cls:
            if species.value == normalized:
                return species
        raise ValueError(f"알 수 없는 수종입니다: {label!r}")
