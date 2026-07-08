from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.email_dto import EmailIntroduceQuery, EmailIntroduceResponse


class GmailPort(ABC):
    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> None: ...

    @abstractmethod
    async def introduce_myself(self, query: EmailIntroduceQuery) -> EmailIntroduceResponse: ...
