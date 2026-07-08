from __future__ import annotations

import os

from dispatch.adapter.outbound.http.telegram_outbound import TelegramBotOutbound
from dispatch.app.ports.input.telegram_use_case import TelegramUseCase
from dispatch.app.use_cases.send_telegram_interactor import SendTelegramInteractor


def get_telegram_use_case() -> TelegramUseCase:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다. suvisdev/.env를 확인하세요.")
    default_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return SendTelegramInteractor(
        telegram=TelegramBotOutbound(bot_token=bot_token),
        default_chat_id=default_chat_id,
    )
