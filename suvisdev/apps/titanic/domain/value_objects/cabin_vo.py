from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cabin:
    value: str

    @classmethod
    def from_raw(cls, raw: str | None) -> Cabin:
        if raw is None:
            return cls(value="")
        return cls(value=raw.strip())

    @property
    def deck(self) -> str | None:
        if self.value and self.value[0].isalpha():
            return self.value[0].upper()
        return None

    def is_unknown(self) -> bool:
        return not self.value.strip()

    def __str__(self) -> str:
        return self.value
