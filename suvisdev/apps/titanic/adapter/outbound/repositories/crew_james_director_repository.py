from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import ensure_titanic_tables, get_mova_session_factory
from titanic.adapter.outbound.orm.passenger_jack_trainer_orm import JackTrainerOrm
from titanic.adapter.outbound.orm.passenger_rose_model_orm import RoseModelOrm
from titanic.app.dtos.crew_james_director_dto import (
    BookingCommand,
    JamesIntroduceQuery,
    JamesIntroduceResponse,
    PassengerCommand,
)
from titanic.app.ports.output.crew_james_director_port import JamesPort

logger = logging.getLogger(__name__)


class JamesRepository(JamesPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: JamesIntroduceQuery) -> JamesIntroduceResponse:
        logger.info("[JamesRepository] introduce_myself 진입 | request_data=%s", query)
        return JamesIntroduceResponse(
            id=query.id * 10000,
            name=query.name + "가 레포지토리에 다녀옴",
        )

    async def receive_uploaded_records(
        self,
        person_commands: list[PassengerCommand],
        booking_commands: list[BookingCommand],
    ) -> int:
        await ensure_titanic_tables()

        if self._session is not None:
            return await self._persist(self._session, person_commands, booking_commands)

        factory = get_mova_session_factory()
        async with factory() as session:
            count = await self._persist(session, person_commands, booking_commands)
            await session.commit()
            return count

    async def _persist(
        self,
        session: AsyncSession,
        person_commands: list[PassengerCommand],
        booking_commands: list[BookingCommand],
    ) -> int:
        if len(person_commands) != len(booking_commands):
            raise ValueError("person_commands와 booking_commands 길이가 일치해야 합니다.")

        passenger_ids = [cmd.passenger_id for cmd in person_commands]
        result = await session.execute(
            select(JackTrainerOrm).where(JackTrainerOrm.passenger_id.in_(passenger_ids)),
        )
        existing_by_passenger_id = {
            person.passenger_id: person for person in result.scalars().all()
        }

        booking_result = await session.execute(
            select(RoseModelOrm.passenger_id).where(RoseModelOrm.passenger_id.in_(passenger_ids)),
        )
        existing_booked_ids = {row for row in booking_result.scalars().all()}

        new_pairs: list[tuple[PassengerCommand, BookingCommand]] = []
        for person_cmd, booking_cmd in zip(person_commands, booking_commands, strict=True):
            if person_cmd.passenger_id in existing_booked_ids:
                continue

            if person_cmd.passenger_id not in existing_by_passenger_id:
                person_row = JackTrainerOrm(
                    passenger_id=person_cmd.passenger_id,
                    name=person_cmd.name,
                    gender=person_cmd.gender,
                    age=person_cmd.age,
                    sib_sp=person_cmd.sib_sp,
                    parch=person_cmd.parch,
                    survived=person_cmd.survived,
                )
                session.add(person_row)
                existing_by_passenger_id[person_cmd.passenger_id] = person_row

            new_pairs.append((person_cmd, booking_cmd))

        await session.flush()

        saved = 0
        for person_cmd, booking_cmd in new_pairs:
            person_row = existing_by_passenger_id[person_cmd.passenger_id]
            session.add(
                RoseModelOrm(
                    passenger_id=person_row.passenger_id,
                    pclass=booking_cmd.pclass,
                    ticket=booking_cmd.ticket,
                    fare=booking_cmd.fare,
                    cabin=booking_cmd.cabin,
                    embarked=booking_cmd.embarked,
                ),
            )
            saved += 1

        if self._session is not None:
            await session.commit()

        return saved
