"""PassengerJackTrainer 엔티티 테스트 — titanic(기준선) 모범 형태.

DDD 엔티티 동등성 규칙(비즈니스 키 passenger_id 기준, 다른 필드는 동등성에
영향 없음)과 상태 변경(update_survival)을 검증한다.
"""

from __future__ import annotations

from titanic.domain.entities.passenger_jack_trainer_entity import PassengerJackTrainer
from titanic.domain.value_objects.passenger_identity_vo import PassengerIdentity
from titanic.domain.value_objects.survived_vo import Survived


def _identity(name: str = "Braund, Mr. Owen Harris", gender: str = "male") -> PassengerIdentity:
    return PassengerIdentity.from_raw(name, gender)


class TestCreate:
    def test_create_with_survived(self) -> None:
        entity = PassengerJackTrainer.create("1", _identity(), Survived.from_raw("1"))
        assert entity.passenger_id == "1"
        assert entity.survived.is_alive is True

    def test_create_without_survived_defaults_to_unknown(self) -> None:
        entity = PassengerJackTrainer.create("1", _identity())
        assert entity.survived.is_alive is None


class TestEquality:
    def test_equal_when_passenger_id_matches_even_if_other_fields_differ(self) -> None:
        a = PassengerJackTrainer.create("1", _identity("Braund, Mr. Owen Harris", "male"), Survived.from_raw("0"))
        b = PassengerJackTrainer.create("1", _identity("Heikkinen, Miss. Laina", "female"), Survived.from_raw("1"))
        assert a == b
        assert hash(a) == hash(b)

    def test_not_equal_when_passenger_id_differs(self) -> None:
        a = PassengerJackTrainer.create("1", _identity())
        b = PassengerJackTrainer.create("2", _identity())
        assert a != b

    def test_not_equal_to_other_types(self) -> None:
        entity = PassengerJackTrainer.create("1", _identity())
        assert entity != "1"
        assert entity.__eq__("1") is NotImplemented


class TestUpdateSurvival:
    def test_update_survival_mutates_survived(self) -> None:
        entity = PassengerJackTrainer.create("1", _identity(), Survived.unknown())
        entity.update_survival(Survived.from_raw("1"))
        assert entity.survived.is_alive is True


class TestSummary:
    def test_summary_includes_id_title_gender_and_survival_label(self) -> None:
        entity = PassengerJackTrainer.create("1", _identity(), Survived.from_raw("1"))
        assert entity.summary() == "[1] Mr male — 생존"

    def test_summary_reports_unknown_survival(self) -> None:
        entity = PassengerJackTrainer.create("1", _identity())
        assert entity.summary() == "[1] Mr male — 미확인"
