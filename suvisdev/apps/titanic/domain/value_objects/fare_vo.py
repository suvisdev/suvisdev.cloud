from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fare:
    value: float | None

    @classmethod
    def from_raw(cls, raw: str | None) -> Fare:
        if raw is None or raw.strip() == "":
            return cls(value=None)
        try:
            return cls(value=float(raw.strip()))
        except ValueError:
            raise ValueError(f"Fare 유효하지 않은 값: '{raw}'")

    @property
    def is_free(self) -> bool | None:
        if self.value is None:
            return None
        return self.value == 0.0

    def __str__(self) -> str:
        return str(self.value) if self.value is not None else ""
