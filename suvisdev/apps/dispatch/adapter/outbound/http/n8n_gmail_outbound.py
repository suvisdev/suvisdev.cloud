from __future__ import annotations

import httpx

from dispatch.app.dtos.email_dto import EmailIntroduceQuery, EmailIntroduceResponse
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.app.ports.output.gmail_port import GmailPort


class N8nGmailOutbound(GmailPort):
    def __init__(self, *, webhook_url: str, timeout: float = 30.0) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout

    def send(self, *, to: str, subject: str, body: str) -> None:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(
                    self._webhook_url, json={"to": to, "subject": subject, "body": body}
                )
        except httpx.TimeoutException as e:
            raise DispatchError("n8n 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise DispatchError(f"n8n 서버에 연결할 수 없습니다: {e!s}", status_code=503) from e
        if r.status_code not in (200, 201):
            raise DispatchError(
                f"n8n 호출 실패 (HTTP {r.status_code}): {r.text[:200]}", status_code=502
            )

    async def introduce_myself(self, query: EmailIntroduceQuery) -> EmailIntroduceResponse:
        return EmailIntroduceResponse(id=query.id, name=query.name)
