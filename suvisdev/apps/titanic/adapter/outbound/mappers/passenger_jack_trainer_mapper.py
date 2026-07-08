from __future__ import annotations

from titanic.adapter.outbound.orm.passenger_jack_trainer_orm import JackTrainerOrm
from titanic.domain.entities.passenger_jack_trainer_entity import PassengerJackTrainer
from titanic.domain.value_objects.passenger_identity_vo import PassengerIdentity
from titanic.domain.value_objects.survived_vo import Survived


class PassengerJackTrainerMapper:
    """JackTrainerOrm ↔ PassengerJackTrainer 변환 — 인프라 계층 전용."""

    @staticmethod
    def to_entity(orm: JackTrainerOrm) -> PassengerJackTrainer:
        return PassengerJackTrainer(
            passenger_id=orm.passenger_id,
            identity=PassengerIdentity.from_raw(orm.name, orm.gender),
            survived=Survived.from_raw(orm.survived),
        )

    @staticmethod
    def to_orm_fields(entity: PassengerJackTrainer) -> dict[str, str]:
        return {
            "passenger_id": entity.passenger_id,
            "name": str(entity.identity.title),
            "gender": str(entity.identity.gender),
            "age": str(entity.identity.age),
            "survived": str(entity.survived),
        }
