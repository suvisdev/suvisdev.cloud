from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EmbarkedType(str, Enum):
    CHERBOURG = "C"
    QUEENSTOWN = "Q"
    SOUTHAMPTON = "S"


_PORT_NAMES: dict[str, str] = {
    "C": "Cherbourg",
    "Q": "Queenstown",
    "S": "Southampton",
}


@dataclass(frozen=True)
class Embarked:
    value: EmbarkedType | None

    @classmethod
    def from_raw(cls, raw: str | None) -> Embarked:
        if raw is None or raw.strip() == "":
            return cls(value=None)
        try:
            return cls(value=EmbarkedType(raw.strip().upper()))
        except (ValueError, KeyError):
            raise ValueError(f"Embarked 유효하지 않은 값: '{raw}'")

    @property
    def port_name(self) -> str:
        if self.value is None:
            return "Unknown"
        return _PORT_NAMES.get(self.value.value, "Unknown")

    def __str__(self) -> str:
        return self.value.value if self.value is not None else ""
