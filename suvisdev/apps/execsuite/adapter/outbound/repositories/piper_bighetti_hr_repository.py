from sqlalchemy.ext.asyncio import AsyncSession

from execsuite.app.dtos.piper_bighetti_hr_dto import BighettiHrQuery, BighettiHrResponse
from execsuite.app.ports.output.piper_bighetti_hr_port import BighettiHrPort


class BighettiHrRepository(BighettiHrPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def introduce_myself(self, query: BighettiHrQuery) -> BighettiHrResponse:
        return BighettiHrResponse(id=query.id, name=query.name)
