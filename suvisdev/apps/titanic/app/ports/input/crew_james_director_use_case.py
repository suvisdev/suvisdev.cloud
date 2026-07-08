from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.adapter.inbound.api.schemas.crew_james_director_schema import JamesIntroduceSchema
from titanic.app.dtos.crew_james_director_dto import JamesIntroduceResponse, JamesResponse


class JamesUseCase(ABC):
    """James CSV 업로드(POST) 입력 포트 (ABC). 조회(GET)는 WalterUseCase."""

    @abstractmethod
    async def receive_uploaded_records(
        self,
        csv_text: str,
    ) -> JamesResponse:
        pass

    @abstractmethod
    async def introduce_myself(
        self,
        schemas: JamesIntroduceSchema,
    ) -> JamesIntroduceResponse:
        pass
