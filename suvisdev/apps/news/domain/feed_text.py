"""피드 요약 칸의 껍데기를 걷어 내고, 요약할 내용이 실제로 있는지 판단한다 (외부 의존 없음).

Hacker News RSS 의 요약 칸은 "Article URL: … Comments URL: … Points: 611 # Comments: 336" 뿐이고, Reddit 링크 글은
"submitted by /u/… [link] [comments]" 뿐이다. 이런 글을 모델에 주면 제목만 보고 지어낸다 — 11-06 운영에서 Martin Fowler 의
'LLM Voice'(글쓰기 말투 이야기)를 "LLM 의 음성 표현 기술"로, Reddit 제목 하나를 "다음 주에 출시될 예정"으로 요약했다.
내용이 없으면 요약하지 않고 제목만 옮긴다.
"""

from __future__ import annotations

import re

MIN_SOURCE_CHARS = 40  # 이보다 짧으면 요약할 내용이 없다고 본다

_HN_META = re.compile(
    r"(?:Article URL:\s*\S*|Comments URL:\s*\S*|Points:\s*\d+|#\s*Comments:\s*\d+)", re.IGNORECASE
)
_REDDIT_TRAILER = re.compile(
    r"submitted\s+by\s+/?u/\S+(?:\s*\[link\])?(?:\s*\[comments\])?\s*$", re.I
)
_BARE_LINKS = re.compile(r"\[(?:link|comments)\]", re.IGNORECASE)


def clean_feed_summary(text: str) -> str:
    """요약 칸에서 링크·점수·작성자 같은 껍데기만 걷어 낸다. 내용이 없으면 빈 문자열."""
    out = _HN_META.sub(" ", text or "")
    out = _REDDIT_TRAILER.sub(" ", out)
    out = _BARE_LINKS.sub(" ", out)
    return " ".join(out.split())


def has_enough_text(summary: str, body: str = "") -> bool:
    """껍데기를 걷어 낸 뒤 요약할 만큼 내용이 남았는가."""
    return len(clean_feed_summary(summary)) + len(clean_feed_summary(body)) >= MIN_SOURCE_CHARS
