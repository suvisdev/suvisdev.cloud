from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GenderType(str, Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass(frozen=True)
class Gender:
    value: GenderType

    @classmethod
    def from_raw(cls, raw: str | None) -> Gender:
        if raw is None or raw.strip() == "":
            raise ValueError("Gender는 필수 값입니다.")
        try:
            return cls(value=GenderType(raw.strip().lower()))
        except (ValueError, KeyError):
            raise ValueError(f"Gender 유효하지 않은 값: '{raw}'")

    @property
    def is_female(self) -> bool:
        return self.value == GenderType.FEMALE

    def __str__(self) -> str:
        return self.value.value
