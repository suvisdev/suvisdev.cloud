from __future__ import annotations

import httpx

from dispatch.app.dtos.discord_dto import DiscordIntroduceQuery, DiscordIntroduceResponse
from dispatch.app.ports.output.discord_port import DiscordPort
from dispatch.app.ports.output.dispatch_errors import DispatchError


class DiscordWebhookOutbound(DiscordPort):
    def __init__(self, *, webhook_url: str, timeout: float = 10.0) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout

    def send(self, *, message: str, username: str | None) -> None:
        payload: dict[str, str] = {"content": message}
        if username:
            payload["username"] = username
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(self._webhook_url, json=payload)
        except httpx.TimeoutException as e:
            raise DispatchError("Discord 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise DispatchError(f"Discord 서버에 연결할 수 없습니다: {e!s}", status_code=503) from e
        if r.status_code not in (200, 204):
            raise DispatchError(
                f"Discord 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

    async def introduce_myself(self, query: DiscordIntroduceQuery) -> DiscordIntroduceResponse:
        return DiscordIntroduceResponse(id=query.id, name=query.name)
