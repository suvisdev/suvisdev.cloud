from __future__ import annotations

import httpx

from dispatch.app.dtos.telegram_dto import TelegramIntroduceQuery, TelegramIntroduceResponse
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.app.ports.output.telegram_port import TelegramPort

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramBotOutbound(TelegramPort):
    def __init__(self, *, bot_token: str, timeout: float = 10.0) -> None:
        self._url = _TELEGRAM_API.format(token=bot_token)
        self._timeout = timeout

    def send(self, *, message: str, chat_id: str) -> None:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(self._url, json={"chat_id": chat_id, "text": message})
        except httpx.TimeoutException as e:
            raise DispatchError("Telegram 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise DispatchError(
                f"Telegram 서버에 연결할 수 없습니다: {e!s}", status_code=503
            ) from e
        if not r.is_success:
            raise DispatchError(
                f"Telegram 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

    async def introduce_myself(self, query: TelegramIntroduceQuery) -> TelegramIntroduceResponse:
        return TelegramIntroduceResponse(id=query.id, name=query.name)
