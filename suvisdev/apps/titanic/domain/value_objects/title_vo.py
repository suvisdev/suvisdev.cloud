from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_RARE_TITLES = {"Capt", "Col", "Don", "Dr", "Major", "Rev", "Jonkheer", "Dona", "Mme"}
_ROYAL_TITLES = {"Countess", "Lady", "Sir"}
_ALIAS = {"Mlle": "Mr", "Ms": "Miss"}


class TitleType(int, Enum):
    MR     = 1
    MISS   = 2
    MRS    = 3
    MASTER = 4
    ROYAL  = 5
    RARE   = 6


_NAME_TO_TYPE: dict[str, TitleType] = {
    "Mr":     TitleType.MR,
    "Miss":   TitleType.MISS,
    "Mrs":    TitleType.MRS,
    "Master": TitleType.MASTER,
    "Royal":  TitleType.ROYAL,
    "Rare":   TitleType.RARE,
}


@dataclass(frozen=True)
class Title:
    value: TitleType

    @classmethod
    def from_name(cls, name: str | None) -> Title:
        if not name:
            raise ValueError("Title: name이 비어 있습니다.")
        match = re.search(r"([A-Za-z]+)\.", name)
        if not match:
            raise ValueError(f"Title: 호칭을 찾을 수 없습니다 — '{name}'")
        raw = match.group(1)
        if raw in _RARE_TITLES:
            raw = "Rare"
        elif raw in _ROYAL_TITLES:
            raw = "Royal"
        else:
            raw = _ALIAS.get(raw, raw)
        title_type = _NAME_TO_TYPE.get(raw)
        if title_type is None:
            raise ValueError(f"Title: 알 수 없는 호칭 — '{raw}'")
        return cls(value=title_type)

    @property
    def code(self) -> int:
        return self.value.value

    def __str__(self) -> str:
        return self.value.name.capitalize()
