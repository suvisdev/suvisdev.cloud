"""대화 스레드 도메인 예외 — 라우터가 status_code로 변환한다."""

from __future__ import annotations


class ConversationNotFoundError(Exception):
    status_code = 404
    detail = "Conversation not found"


class ConversationForbiddenError(Exception):
    status_code = 403
    detail = "본인 대화만 접근할 수 있습니다."
