"""Title/Gender/PassengerIdentity/Survived VO 테스트 — titanic(기준선) 모범 형태.

VO는 frozen dataclass + 팩토리(from_raw/from_name)로 생성하고, 원본 문자열이
잘못됐을 때 ValueError로 즉시 실패한다는 걸 검증한다. mova/gildle도 같은
"필드 하나가 아니라 개념 하나당 VO 하나" 컨벤션을 쓰므로, 여기서 검증하는
불변성·팩토리 검증 패턴을 그대로 참고할 수 있다.
"""

from __future__ import annotations

import dataclasses

import pytest

from titanic.domain.value_objects.gender_vo import Gender, GenderType
from titanic.domain.value_objects.passenger_identity_vo import PassengerIdentity
from titanic.domain.value_objects.survived_vo import Survived, SurvivedType
from titanic.domain.value_objects.title_vo import Title, TitleType


class TestTitle:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("Braund, Mr. Owen Harris", TitleType.MR),
            ("Heikkinen, Miss. Laina", TitleType.MISS),
            ("Futrelle, Mrs. Jacques Heath (Lily May Peel)", TitleType.MRS),
            ("Palsson, Master. Gosta Leonard", TitleType.MASTER),
        ],
    )
    def test_from_name_maps_common_titles(self, name: str, expected: TitleType) -> None:
        assert Title.from_name(name).value == expected

    def test_from_name_maps_rare_titles_to_rare(self) -> None:
        assert Title.from_name("Someone, Dr. Foo").value == TitleType.RARE
        assert Title.from_name("Someone, Col. Foo").value == TitleType.RARE

    def test_from_name_maps_royal_titles(self) -> None:
        assert Title.from_name("Someone, Countess. Foo").value == TitleType.ROYAL
        assert Title.from_name("Someone, Sir. Foo").value == TitleType.ROYAL

    def test_from_name_applies_alias(self) -> None:
        assert Title.from_name("Someone, Mlle. Foo").value == TitleType.MR
        assert Title.from_name("Someone, Ms. Foo").value == TitleType.MISS

    def test_from_name_raises_on_empty(self) -> None:
        with pytest.raises(ValueError):
            Title.from_name("")
        with pytest.raises(ValueError):
            Title.from_name(None)

    def test_from_name_raises_when_no_title_pattern(self) -> None:
        with pytest.raises(ValueError):
            Title.from_name("이름에 호칭이 없음")

    def test_is_frozen(self) -> None:
        title = Title.from_name("Braund, Mr. Owen Harris")
        with pytest.raises(dataclasses.FrozenInstanceError):
            title.value = TitleType.MISS  # type: ignore[misc]

    def test_str_capitalizes_type_name(self) -> None:
        assert str(Title.from_name("Braund, Mr. Owen Harris")) == "Mr"


class TestGender:
    @pytest.mark.parametrize("raw", ["male", "MALE", " Male "])
    def test_from_raw_parses_male(self, raw: str) -> None:
        gender = Gender.from_raw(raw)
        assert gender.value == GenderType.MALE
        assert gender.is_female is False

    @pytest.mark.parametrize("raw", ["female", "FEMALE"])
    def test_from_raw_parses_female(self, raw: str) -> None:
        gender = Gender.from_raw(raw)
        assert gender.value == GenderType.FEMALE
        assert gender.is_female is True

    def test_from_raw_raises_on_empty_or_none(self) -> None:
        with pytest.raises(ValueError):
            Gender.from_raw("")
        with pytest.raises(ValueError):
            Gender.from_raw(None)

    def test_from_raw_raises_on_unknown_value(self) -> None:
        with pytest.raises(ValueError):
            Gender.from_raw("unknown")

    def test_is_frozen(self) -> None:
        gender = Gender.from_raw("male")
        with pytest.raises(dataclasses.FrozenInstanceError):
            gender.value = GenderType.FEMALE  # type: ignore[misc]


class TestPassengerIdentity:
    def test_from_raw_combines_title_and_gender(self) -> None:
        identity = PassengerIdentity.from_raw("Braund, Mr. Owen Harris", "male")
        assert identity.title.value == TitleType.MR
        assert identity.gender.value == GenderType.MALE

    def test_is_female_delegates_to_gender(self) -> None:
        female = PassengerIdentity.from_raw("Heikkinen, Miss. Laina", "female")
        male = PassengerIdentity.from_raw("Braund, Mr. Owen Harris", "male")
        assert female.is_female is True
        assert male.is_female is False

    def test_str_combines_title_and_gender(self) -> None:
        identity = PassengerIdentity.from_raw("Braund, Mr. Owen Harris", "male")
        assert str(identity) == "Mr / male"

    def test_is_frozen(self) -> None:
        identity = PassengerIdentity.from_raw("Braund, Mr. Owen Harris", "male")
        with pytest.raises(dataclasses.FrozenInstanceError):
            identity.title = Title.from_name("Heikkinen, Miss. Laina")  # type: ignore[misc]


class TestSurvived:
    def test_from_raw_parses_dead_and_alive(self) -> None:
        assert Survived.from_raw("0").value == SurvivedType.DEAD
        assert Survived.from_raw("1").value == SurvivedType.ALIVE

    def test_from_raw_none_or_blank_is_unknown(self) -> None:
        assert Survived.from_raw(None).value is None
        assert Survived.from_raw("").value is None
        assert Survived.from_raw("  ").value is None

    def test_from_raw_raises_on_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            Survived.from_raw("2")
        with pytest.raises(ValueError):
            Survived.from_raw("not-a-number")

    def test_unknown_factory(self) -> None:
        assert Survived.unknown().value is None
        assert Survived.unknown().is_alive is None

    def test_is_alive_reflects_value(self) -> None:
        assert Survived.from_raw("1").is_alive is True
        assert Survived.from_raw("0").is_alive is False
        assert Survived.unknown().is_alive is None

    def test_str_round_trips_raw_value(self) -> None:
        assert str(Survived.from_raw("1")) == "1"
        assert str(Survived.from_raw("0")) == "0"
        assert str(Survived.unknown()) == ""

    def test_is_frozen(self) -> None:
        survived = Survived.from_raw("1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            survived.value = SurvivedType.DEAD  # type: ignore[misc]
