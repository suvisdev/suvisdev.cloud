"""서수 지시어 해석 — "두번째꺼 어디서 볼 수 있어"의 '두번째꺼'를 직전 추천 카드의 제목으로 바꾼다.

추천 카드 제목은 화면에만 있고 응답 문장에는 없어서, 모델(7.8B든 2.4B든)이 받는 대화 기록만으로는
"두번째"가 무엇인지 알 수 없었다(2026-09-28 실사용: "예매하실 작품을 카탈로그에서 찾지 못했어요").
프론트가 assistant 턴 앞에 `[추천 카드] 1.『A』(2007) 2.『B』(2021)`를 붙여 보내고, 여기서 발화의
서수를 그 제목으로 치환한 뒤 이해 단계로 넘긴다 — 모델이 추론할 필요가 없게 결정론으로.
"""

from __future__ import annotations

import re

CARD_LIST_MARK = "[추천 카드]"
_CARD_ITEM = re.compile(r"(\d)\.\s*『([^』]+)』")
_SUFFIX = r"(?:\s*(?:꺼|거|것|영화|작품))?"
_ORDINAL = re.compile(
    r"(첫\s*번째|첫째|두\s*번째|둘째|세\s*번째|셋째|네\s*번째|다섯\s*번째|(?<!\d)([1-5])\s*번(?!\s*더))"
    + _SUFFIX
)
_LAST = re.compile(r"마지막\s*(?:꺼|거|것|영화|작품)")
_ORD_WORD = {"첫": 1, "두": 2, "둘": 2, "세": 3, "셋": 3, "네": 4, "다섯": 5}


def _last_assistant(history: list[dict[str, str]]) -> str:
    for m in reversed(history):
        if m.get("role") == "assistant":
            return m.get("content") or ""
    return ""


def resolve_ordinal_reference(message: str, history: list[dict[str, str]]) -> str | None:
    """서수가 직전 추천 카드 목록을 가리키면 제목으로 치환한 발화를, 아니면 None."""
    last = _last_assistant(history)
    if CARD_LIST_MARK not in last:
        return None
    titles = {int(n): t.strip() for n, t in _CARD_ITEM.findall(last.split(CARD_LIST_MARK, 1)[1])}
    if not titles:
        return None
    m = _LAST.search(message)
    if m:
        idx = max(titles)
    else:
        m = _ORDINAL.search(message)
        if not m:
            return None
        word = m.group(1).replace(" ", "")
        if m.group(2):
            idx = int(m.group(2))
        else:
            idx = next((v for k, v in _ORD_WORD.items() if word.startswith(k)), 0)
    title = titles.get(idx)
    if not title:
        return None
    return re.sub(r"\s+", " ", f"{message[: m.start()]} {title} {message[m.end() :]}").strip()
