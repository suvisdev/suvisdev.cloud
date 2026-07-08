"""어시스턴트 VO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantSlug:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 64:
            raise ValueError(f"AssistantSlug must be 1-64 chars: {self.value!r}")
