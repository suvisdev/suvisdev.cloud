from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FaceTrainResult:
    weights_path: str
    class_names: list[str]
    epochs: int


@dataclass(frozen=True)
class FacePredictResult:
    predicted_name: str
    confidence: float
