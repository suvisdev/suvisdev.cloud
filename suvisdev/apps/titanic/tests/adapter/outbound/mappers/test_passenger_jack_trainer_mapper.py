"""PassengerJackTrainerMapper 테스트 — titanic(기준선) 모범 형태.

핵심 포인트: to_entity()는 실제 JackTrainerOrm(SQLAlchemy) 타입에 의존하지
않고 passenger_id/name/gender/survived 속성만 있으면 동작한다(DIP) — 그래서
진짜 ORM 대신 같은 모양의 가짜(SimpleNamespace)로 스왑해도 결과가 같다는
걸 별도로 검증한다. 인프라(ORM)를 몰라도 도메인 계층 매핑 규칙을 테스트할
수 있다는 게 이 패턴의 핵심이다.
"""

from __future__ import annotations

from types import SimpleNamespace

from titanic.adapter.outbound.mappers.passenger_jack_trainer_mapper import (
    PassengerJackTrainerMapper,
)
from titanic.adapter.outbound.orm.passenger_jack_trainer_orm import JackTrainerOrm
from titanic.domain.entities.passenger_jack_trainer_entity import PassengerJackTrainer
from titanic.domain.value_objects.passenger_identity_vo import PassengerIdentity
from titanic.domain.value_objects.survived_vo import Survived

_RAW_FIELDS = dict(
    passenger_id="1",
    name="Braund, Mr. Owen Harris",
    gender="male",
    age="22",
    sib_sp="1",
    parch="0",
    survived="0",
)


class TestToEntity:
    def test_maps_real_orm_to_entity(self) -> None:
        orm = JackTrainerOrm(**_RAW_FIELDS)

        entity = PassengerJackTrainerMapper.to_entity(orm)

        assert entity.passenger_id == "1"
        assert entity.identity.title.code == 1  # Mr
        assert entity.identity.gender.is_female is False
        assert entity.survived.is_alive is False

    def test_maps_fake_adapter_with_same_shape_to_identical_entity(self) -> None:
        """DIP 스왑: 실제 ORM 대신 같은 속성만 가진 가짜로 바꿔도 결과가 같다."""
        fake_orm = SimpleNamespace(**_RAW_FIELDS)
        real_orm = JackTrainerOrm(**_RAW_FIELDS)

        from_fake = PassengerJackTrainerMapper.to_entity(fake_orm)  # type: ignore[arg-type]
        from_real = PassengerJackTrainerMapper.to_entity(real_orm)

        assert from_fake == from_real
        assert from_fake.identity == from_real.identity
        assert from_fake.survived == from_real.survived


class TestToOrmFields:
    def test_round_trips_back_to_raw_shaped_dict(self) -> None:
        entity = PassengerJackTrainer.create(
            "1",
            PassengerIdentity.from_raw("Braund, Mr. Owen Harris", "male"),
            Survived.from_raw("0"),
        )

        fields = PassengerJackTrainerMapper.to_orm_fields(entity)

        assert fields == {
            "passenger_id": "1",
            "name": "Mr",
            "gender": "male",
            "survived": "0",
        }
