from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.adapter.inbound.api.schemas.email_schema import EmailIntroduceSchema
from dispatch.app.dtos.email_dto import EmailDto, EmailIntroduceResponse


class EmailUseCase(ABC):
    @abstractmethod
    def send(self, *, to: str, prompt: str, subject: str | None) -> EmailDto: ...

    @abstractmethod
    async def introduce_myself(self, schema: EmailIntroduceSchema) -> EmailIntroduceResponse: ...
