from __future__ import annotations

from dataclasses import dataclass, field

from titanic.domain.value_objects.berth_vo import Berth
from titanic.domain.value_objects.embarked_vo import Embarked


@dataclass
class Booking:
    """
    Booking Domain Entity — DDD 엄격 적용.

    동등성 기준 : passenger_id (비즈니스 키)
    ORM 매핑   : 인프라 계층(PassengerRoseModelMapper)에서 담당 — 엔티티는 ORM을 모른다.
    _db_id     : 인프라 전용 PK; 도메인 로직에서 직접 참조 금지.
    """

    passenger_id: str
    berth: Berth
    embarked: Embarked

    _db_id: int | None = field(default=None, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Booking):
            return NotImplemented
        return self.passenger_id == other.passenger_id

    def __hash__(self) -> int:
        return hash(self.passenger_id)

    def is_first_class(self) -> bool:
        return self.berth.is_upper_class

    def deck(self) -> str | None:
        return self.berth.deck

    def embarkation_port(self) -> str:
        return self.embarked.port_name

    def summary(self) -> str:
        return (
            f"[person:{self.passenger_id}] {self.berth} "
            f"/ 승선:{self.embarked.port_name}"
        )

    @classmethod
    def create(
        cls,
        passenger_id: str,
        berth: Berth,
        embarked: Embarked,
    ) -> Booking:
        return cls(
            passenger_id=passenger_id,
            berth=berth,
            embarked=embarked,
        )
