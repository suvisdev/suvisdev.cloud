from sqlalchemy.ext.asyncio import AsyncSession

from execsuite.app.dtos.piper_hendricks_ceo_dto import HendricksCeoQuery, HendricksCeoResponse
from execsuite.app.ports.output.piper_hendricks_ceo_port import HendricksCeoPort


class HendricksCeoRepository(HendricksCeoPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def introduce_myself(self, query: HendricksCeoQuery) -> HendricksCeoResponse:
        return HendricksCeoResponse(id=query.id, name=query.name)
