"""반려견 동반 산책 중 들를 만한 장소(동물병원·펫샵·용품점·애견카페) — 2026-09-28."""

from __future__ import annotations

from dataclasses import dataclass

from gildle.domain.value_objects.coordinate import Coordinate

PET_PLACE_CATEGORIES = ("동물병원", "펫샵", "용품점", "애견카페")


@dataclass(frozen=True)
class PetPlace:
    place_id: str
    name: str
    category: str  # PET_PLACE_CATEGORIES 중 하나
    coordinate: Coordinate
    address: str = ""
    url: str = ""
    phone: str = ""
