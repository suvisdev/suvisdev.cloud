from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float
