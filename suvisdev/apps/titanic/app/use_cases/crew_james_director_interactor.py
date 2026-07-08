from __future__ import annotations

import csv
from io import StringIO

from titanic.adapter.inbound.api.schemas.crew_james_director_schema import (
    JamesIntroduceSchema,
    JamesSchema,
)
from titanic.app.dtos.crew_james_director_dto import (
    BookingCommand,
    JamesIntroduceQuery,
    JamesIntroduceResponse,
    JamesResponse,
    PassengerCommand,
)
from titanic.app.ports.input.crew_james_director_use_case import JamesUseCase
from titanic.app.ports.output.crew_james_director_port import JamesPort


class JamesInteractor(JamesUseCase):
    """crew_james_director_router → 입력 포트 → 출력 포트(repository)."""

    def __init__(self, repository: JamesPort) -> None:
        self._repository = repository

    def _normalize_row(self, row: dict) -> dict:
        normalized: dict[str, str] = {}
        for raw_key, value in row.items():
            if raw_key is None:
                continue
            key = raw_key.strip()
            lower_key = key.lower()
            if lower_key == "sex":
                normalized["gender"] = value
            elif lower_key == "passengerid":
                normalized["passenger_id"] = value
            elif lower_key == "sibsp":
                normalized["sib_sp"] = value
            elif lower_key in {
                "survived", "pclass", "name", "age", "parch",
                "ticket", "fare", "cabin", "embarked", "gender",
            }:
                normalized[lower_key] = value
            else:
                normalized[key] = value
        return normalized

    def _parse_csv(self, text: str) -> list[JamesSchema]:
        if not text.strip():
            raise ValueError("빈 CSV 파일입니다.")
        reader = csv.DictReader(StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("CSV 헤더를 읽을 수 없습니다.")
        return [JamesSchema(**self._normalize_row(row)) for row in reader]

    async def receive_uploaded_records(self, csv_text: str) -> JamesResponse:
        schemas = self._parse_csv(csv_text)
        person_commands = [
            PassengerCommand(
                passenger_id=schema.passenger_id,
                name=schema.name,
                gender=schema.gender,
                age=schema.age,
                sib_sp=schema.sib_sp,
                parch=schema.parch,
                survived=schema.survived,
            )
            for schema in schemas
        ]
        booking_commands = [
            BookingCommand(
                pclass=schema.pclass,
                ticket=schema.ticket,
                fare=schema.fare,
                cabin=schema.cabin,
                embarked=schema.embarked,
            )
            for schema in schemas
        ]
        saved = await self._repository.receive_uploaded_records(
            person_commands,
            booking_commands,
        )
        return JamesResponse(answer=str(saved))

    async def introduce_myself(
        self,
        schemas: JamesIntroduceSchema,
    ) -> JamesIntroduceResponse:
        return await self._repository.introduce_myself(
            JamesIntroduceQuery(id=schemas.id, name=schemas.name),
        )
