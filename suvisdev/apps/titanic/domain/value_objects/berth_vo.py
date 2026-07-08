from __future__ import annotations

from dataclasses import dataclass

from titanic.domain.value_objects.cabin_vo import Cabin
from titanic.domain.value_objects.fare_vo import Fare
from titanic.domain.value_objects.pclass_vo import PClass


@dataclass(frozen=True)
class Berth:
    """선실 등급·객실 구역·탑승 요금 묶음.

    pclass ↔ fare (-0.55), pclass ↔ cabin (-0.38), fare ↔ cabin (+0.34) 강상관.
    세 피처가 모두 선박 내 사회적 위치를 표현하므로 하나의 값 타입으로 묶는다.
    """

    pclass: PClass
    cabin: Cabin
    fare: Fare

    @classmethod
    def from_raw(
        cls,
        pclass: str | None,
        cabin: str | None,
        fare: str | None,
    ) -> Berth:
        return cls(
            pclass=PClass.from_raw(pclass),
            cabin=Cabin.from_raw(cabin),
            fare=Fare.from_raw(fare),
        )

    @property
    def is_upper_class(self) -> bool:
        return self.pclass.is_first_class

    @property
    def deck(self) -> str | None:
        return self.cabin.deck

    def __str__(self) -> str:
        deck_text = self.cabin.deck or "미확인"
        return f"{self.pclass}등석 / 데크:{deck_text} / 요금:{self.fare}"
