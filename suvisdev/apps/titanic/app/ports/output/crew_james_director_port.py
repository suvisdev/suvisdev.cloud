from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.app.dtos.crew_james_director_dto import (
    BookingCommand,
    JamesIntroduceQuery,
    JamesIntroduceResponse,
    JamesResponse,
    PassengerCommand,
)


class JamesPort(ABC):
    """James 업로드 데이터를 외부로 보내는 아웃바운드 포트 (ABC)."""

    @abstractmethod
    async def receive_uploaded_records(
        self,
        person_commands: list[PassengerCommand],
        booking_commands: list[BookingCommand],
    ) -> JamesResponse:
        pass

    @abstractmethod
    async def introduce_myself(self, query: JamesIntroduceQuery) -> JamesIntroduceResponse:
        pass
