from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.app.dtos.crew_lowe_boat_dto import LoweBoatQuery, LoweBoatResponse


class LoweBoatPort(ABC):
    """crew_lowe_boat output port."""

    @abstractmethod
    def introduce_myself(self, query: LoweBoatQuery)->LoweBoatResponse:
        pass
