from __future__ import annotations

from titanic.adapter.outbound.orm.passenger_rose_model_orm import RoseModelOrm
from titanic.domain.entities.passenger_rose_model_entity import Booking
from titanic.domain.value_objects.berth_vo import Berth
from titanic.domain.value_objects.embarked_vo import Embarked


class PassengerRoseModelMapper:
    """RoseModelOrm ↔ Booking 변환 — 인프라 계층 전용."""

    @staticmethod
    def to_entity(orm: RoseModelOrm) -> Booking:
        return Booking(
            passenger_id=orm.passenger_id,
            berth=Berth.from_raw(orm.pclass, orm.cabin, orm.fare),
            embarked=Embarked.from_raw(orm.embarked),
            _db_id=orm.id,
        )

    @staticmethod
    def to_orm_fields(entity: Booking) -> dict[str, str]:
        return {
            "passenger_id": entity.passenger_id,
            "pclass": str(entity.berth.pclass),
            "fare": str(entity.berth.fare),
            "cabin": str(entity.berth.cabin),
            "embarked": str(entity.embarked),
        }
