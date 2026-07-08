"""스팸 카테고리 — 분류 가능한 레이블 상수."""

from __future__ import annotations

from enum import Enum


class SpamCategory(str, Enum):
    ADVERTISING = "광고"
    PHISHING = "피싱"
    MALWARE = "악성코드"
    BULK = "대량발송"
    SCAM = "사기"
    HAM = "정상"

    @property
    def is_spam(self) -> bool:
        return self is not SpamCategory.HAM
