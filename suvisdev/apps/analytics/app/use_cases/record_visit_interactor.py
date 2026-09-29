from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from analytics.app.ports.input.record_visit_use_case import RecordVisitUseCase
from analytics.app.ports.output.visitor_activity_repository import VisitorActivityRepository

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")
# 크롤러·링크 미리보기·헤드리스 브라우저·CLI. UA가 없어도 봇(브라우저는 항상 보낸다).
_BOT_UA = re.compile(
    r"bot|crawl|spider|slurp|headless|phantom|puppeteer|playwright|selenium|lighthouse|"
    r"preview|scrap|fetch|curl|wget|python-requests|httpx|go-http-client|java/|"
    r"inspectiontool|facebookexternalhit|kakaotalk|twitterbot|discordbot|slackbot|whatsapp|"
    r"telegrambot|yeti|daum|bingbot|baiduspider|yandex|duckduck|petalbot|semrush|ahrefs|mj12|dotbot",
    re.IGNORECASE,
)


def is_bot_user_agent(user_agent: str | None) -> bool:
    ua = (user_agent or "").strip()
    return not ua or bool(_BOT_UA.search(ua))


class RecordVisitInteractor(RecordVisitUseCase):
    def __init__(self, *, repository: VisitorActivityRepository) -> None:
        self._repository = repository

    async def record(self, visitor_id: str, user_agent: str | None = None) -> None:
        try:
            uuid.UUID(visitor_id)
        except (ValueError, AttributeError, TypeError):
            # 조작되거나 형식이 틀린 값은 집계에서 조용히 제외한다(공개 엔드포인트라 서버가 죽으면 안 됨).
            logger.warning("[RecordVisitInteractor] 유효하지 않은 visitor_id 무시")
            return

        now = datetime.now(UTC)
        visit_date = now.astimezone(_KST).date()
        await self._repository.upsert_visit(
            visitor_id,
            visit_date,
            now,
            is_bot=is_bot_user_agent(user_agent),
            user_agent=(user_agent or "")[:256] or None,
        )
