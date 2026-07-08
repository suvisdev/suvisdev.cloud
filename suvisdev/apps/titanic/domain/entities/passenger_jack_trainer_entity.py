from __future__ import annotations

from dataclasses import dataclass

from titanic.domain.value_objects.passenger_identity_vo import PassengerIdentity
from titanic.domain.value_objects.survived_vo import Survived


@dataclass
class PassengerJackTrainer:
    """
    Passenger Domain Entity — DDD 엄격 적용.

    동등성 기준 : passenger_id (비즈니스 키)
    ORM 매핑   : 인프라 계층(JackTrainerRepository)에서 담당 — 엔티티는 ORM을 모른다.
    """

    passenger_id: str
    identity: PassengerIdentity
    survived: Survived

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PassengerJackTrainer):
            return NotImplemented
        return self.passenger_id == other.passenger_id

    def __hash__(self) -> int:
        return hash(self.passenger_id)

    def update_survival(self, new_survived: Survived) -> None:
        self.survived = new_survived

    def summary(self) -> str:
        survived_label = {True: "생존", False: "사망", None: "미확인"}[
            self.survived.is_alive
        ]
        return (
            f"[{self.passenger_id}] {self.identity.title} {self.identity.gender} "
            f"({self.identity.age}세) — {survived_label}"
        )

    @classmethod
    def create(
        cls,
        passenger_id: str,
        identity: PassengerIdentity,
        survived: Survived | None = None,
    ) -> PassengerJackTrainer:
        return cls(
            passenger_id=passenger_id,
            identity=identity,
            survived=survived or Survived.unknown(),
        )
