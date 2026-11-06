"""한국어 제목·요약 검사 규칙 (외부 의존 없음).

영어 글(논문·연구소 블로그·릴리스·해설·커뮤니티)은 노트북 올라마 EXAONE 7.8B 로 제목을 옮기고 2~3문장으로 요약한다.
한국어 글은 요약만 한다 — 제목은 원문 그대로 둔다(11-05 시험에서 모델이 한국어 제목의 표현을 바꿨다).
모델 출력이 형식에 안 맞으면 저장하지 않는다(실패 횟수만 센다).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

MAX_TITLE = 200
MAX_SUMMARY = 600
MIN_SUMMARY = 20
_HANGUL = re.compile(r"[가-힣]")
_LETTER = re.compile(r"[A-Za-z가-힣]")
_JSON_OBJECT = re.compile(r"\{.*\}", re.S)


@dataclass(frozen=True)
class KoSummary:
    title_ko: str
    summary_ko: str


def is_korean(text: str) -> bool:
    """글자 중 한글이 30% 이상이면 한국어로 본다(영문 고유명사가 섞인 국내 기사 제목을 위해)."""
    letters = _LETTER.findall(text)
    if not letters:
        return False
    return sum(1 for ch in letters if _HANGUL.match(ch)) / len(letters) >= 0.3


def parse_title_only(raw: str, original_title: str) -> KoSummary | None:
    """내용 없는 글의 제목 번역 응답. 요약은 비워 둔다(빈 문자열 = '요약할 내용 없음', 다시 시도하지 않는다)."""
    match = _JSON_OBJECT.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    title = data.get("title_ko") if isinstance(data, dict) else None
    if not isinstance(title, str) or not title.strip():
        return None
    # 한글이 없으면 원제를 둔다 — 이름뿐인 제목('Kimi K3')은 옮길 게 없고, 다른 영어로 바꿔 쓴 답은 믿을 수 없다
    kept = title if _HANGUL.search(title) else original_title
    return KoSummary(title_ko=" ".join(kept.split())[:MAX_TITLE], summary_ko="")


def parse_ko_summary(raw: str, original_title: str) -> KoSummary | None:
    """모델 출력(JSON) → KoSummary. 형식이 틀리거나 요약에 한글이 없으면 None."""
    match = _JSON_OBJECT.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    title = data.get("title_ko")
    summary = data.get("summary_ko")
    if not isinstance(summary, str):
        return None
    summary = " ".join(summary.split())
    if not (MIN_SUMMARY <= len(summary) <= MAX_SUMMARY) or not _HANGUL.search(summary):
        return None
    if is_korean(original_title) or not isinstance(title, str) or not title.strip():
        title = original_title
    title = " ".join(title.split())[:MAX_TITLE]
    return KoSummary(title_ko=title, summary_ko=summary)
