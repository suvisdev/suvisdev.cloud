"""picks DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PickFeedbackDto:
    pick_id: int
    feedback: str | None
    updated: bool
