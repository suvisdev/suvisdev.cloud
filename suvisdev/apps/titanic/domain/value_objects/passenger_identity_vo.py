from __future__ import annotations

from dataclasses import dataclass

from titanic.domain.value_objects.gender_vo import Gender
from titanic.domain.value_objects.title_vo import Title


@dataclass(frozen=True)
class PassengerIdentity:
    """호칭·성별 묶음.

    survived 상관: gender(+0.54) > title(+0.37).
    title이 gender를 내포하므로 함께 묶어 생존 예측의 핵심 신호를 표현한다.
    """

    title: Title
    gender: Gender

    @classmethod
    def from_raw(cls, name: str, gender: str) -> PassengerIdentity:
        return cls(
            title=Title.from_name(name),
            gender=Gender.from_raw(gender),
        )

    @property
    def is_female(self) -> bool:
        return self.gender.is_female

    def __str__(self) -> str:
        return f"{self.title} / {self.gender}"
