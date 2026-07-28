from sqlalchemy.ext.asyncio import AsyncSession

from execsuite.app.dtos.piper_dinesh_dash_dto import DineshDashQuery, DineshDashResponse
from execsuite.app.ports.output.piper_dinesh_dash_port import DineshDashPort


class DineshDashRepository(DineshDashPort):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def introduce_myself(self, query: DineshDashQuery) -> DineshDashResponse:
        return DineshDashResponse(id=query.id, name=query.name)
