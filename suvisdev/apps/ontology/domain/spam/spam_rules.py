"""스팸 판별 규칙 — LLM 호출 전 빠른 사전 필터."""

from __future__ import annotations

from ontology.domain.spam.spam_category import SpamCategory

_PHISHING_KEYWORDS: frozenset[str] = frozenset(
    {"비밀번호", "계정 확인", "로그인 정보", "본인 인증", "클릭하세요", "account verify"}
)
_SCAM_KEYWORDS: frozenset[str] = frozenset(
    {"투자 수익", "무료 지급", "당첨", "긴급 송금", "billion", "lottery"}
)
_BULK_KEYWORDS: frozenset[str] = frozenset(
    {"수신 거부", "unsubscribe", "광고", "홍보", "이벤트 안내"}
)


def quick_filter(*, subject: str, body: str) -> SpamCategory | None:
    """키워드 기반 사전 필터. 확실한 경우만 반환, 불확실하면 None(→ LLM 판단)."""
    text = (subject + " " + body).lower()
    if any(kw.lower() in text for kw in _PHISHING_KEYWORDS):
        return SpamCategory.PHISHING
    if any(kw.lower() in text for kw in _SCAM_KEYWORDS):
        return SpamCategory.SCAM
    if any(kw.lower() in text for kw in _BULK_KEYWORDS):
        return SpamCategory.BULK
    return None
