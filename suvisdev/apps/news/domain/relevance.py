"""검색어 관련성 점수 (외부 의존 없는 계산 규칙 — §P 도메인 서비스).

뉴스 검색 API 는 본문 어딘가에 단어만 있어도 결과에 넣는다. 그래서 제목·요약 기준으로 한 번 더
거른다. AI 판정과는 별개다 — 관련 없는 기사는 저장하지 않고, AI 기사는 빼지 않고 배지를 단다.
기준값은 정답셋이 생기면 재서 고친다(newsdesk 하네스 eval-protocol.md).
"""

from __future__ import annotations

import re

RELEVANCE_MIN = 0.5
_NON_WORD = re.compile(r"[^0-9a-z가-힣]")


def _norm(text: str) -> str:
    return _NON_WORD.sub("", text.lower())


def relevance(query: str, title: str, lead: str = "") -> float:
    """0~1. 제목에 검색어 전체 1.0 · 제목에 단어 전부 0.8 · 요약(첫 문단)에 검색어 0.6 · 그 밖은 부분 점수."""
    q = _norm(query)
    tokens = [t for t in (_norm(w) for w in query.split()) if t]
    if not q or not tokens:
        return 0.0
    t, ld = _norm(title), _norm(lead)
    if q in t:
        return 1.0
    title_cov = sum(tok in t for tok in tokens) / len(tokens)
    if title_cov == 1.0:
        return 0.8
    lead_cov = sum(tok in ld for tok in tokens) / len(tokens)
    if q in ld or lead_cov == 1.0:
        return 0.6
    return round(0.5 * title_cov + 0.3 * lead_cov, 2)


def is_relevant(score: float) -> bool:
    return score >= RELEVANCE_MIN
