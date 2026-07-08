from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SurvivedType(int, Enum):
    DEAD = 0
    ALIVE = 1


@dataclass(frozen=True)
class Survived:
    value: SurvivedType | None

    @classmethod
    def from_raw(cls, raw: str | None) -> Survived:
        if raw is None or raw.strip() == "":
            return cls(value=None)
        try:
            return cls(value=SurvivedType(int(raw.strip())))
        except (ValueError, KeyError):
            raise ValueError(f"Survived 유효하지 않은 값: '{raw}'")

    @classmethod
    def unknown(cls) -> Survived:
        return cls(value=None)

    @property
    def is_alive(self) -> bool | None:
        if self.value is None:
            return None
        return self.value == SurvivedType.ALIVE

    def __str__(self) -> str:
        return str(self.value.value) if self.value is not None else ""
