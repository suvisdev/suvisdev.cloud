"""영화 제목 값 객체 — "같은 제목인가"의 규칙을 한곳에 둔다(2026-09-27).

같은 정규화가 오케스트레이터·제목 해석기·예매 서비스·PG 저장소 네 곳에 각자 복사돼 있었다
(공백 제거+소문자 3곳, 구두점까지 제거 1곳). 한 곳이 바뀌면 나머지가 어긋나는 구조라
값 객체로 모았다 — 아키텍처 감사(WORK_LOG_MAINPAGE 09-27) 뒤 "DDD는 규칙이 중복되는
곳에만"의 첫 적용.

- `key`: 공백 제거 + 소문자. 카탈로그 정확 일치·동명 작품 판정.
- `loose_key`: 구두점(·:『』 등)까지 제거. 문장 안에 제목이 들어 있는지 볼 때(역조회).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WS = re.compile(r"\s+")
_LOOSE = re.compile(r"[\s:·『』\"'(),.!?~\-]")
_MIN_LOOSE_LEN = 3  # 2자 이하 제목은 문장 포함 판정에서 오탐이 커 제외


def normalize_title(text: str) -> str:
    return _WS.sub("", text).lower()


def loose_title_key(text: str) -> str:
    return _LOOSE.sub("", text).lower()


# 번호 앞 공백 필수 — "1987"·"300"처럼 숫자뿐인 제목이 빈 키로 뭉치지 않게
_SEQUEL_TAIL = re.compile(r"\s+(?:\d+|[IVX]+|시즌\s*\d+|part\s*\d+)$", re.IGNORECASE)


def series_key(text: str) -> str:
    """같은 시리즈 판정 — 부제(콜론 뒤)와 끝 번호를 뗀다("범죄도시 3"·"나쁜 녀석들: 포에버" → 본편).

    추천 3편 다양성(MOVA_RECOMMENDATION_CRITERIA §2-3)에 쓴다. 하네스 `eval_chat_queries.py`의
    `series_dup` 지표도 같은 규칙이다(스크립트는 앱 import 없이 돌아야 해서 사본을 둔다).
    """
    base = re.split(r"[:：]", text, maxsplit=1)[0].strip()
    return normalize_title(_SEQUEL_TAIL.sub("", base)) or normalize_title(text)


@dataclass(frozen=True)
class MovieTitle:
    raw: str

    @property
    def key(self) -> str:
        return normalize_title(self.raw)

    @property
    def loose_key(self) -> str:
        return loose_title_key(self.raw)

    def equals(self, other: MovieTitle | str) -> bool:
        other_key = other.key if isinstance(other, MovieTitle) else normalize_title(other)
        return self.key == other_key

    def appears_in(self, text: str) -> bool:
        """text 안에 이 제목이 (공백·구두점 무시하고) 들어 있는가. 2자 이하는 항상 False."""
        k = self.loose_key
        return len(k) >= _MIN_LOOSE_LEN and k in loose_title_key(text)

    def overlaps(self, other: MovieTitle | str) -> bool:
        """한쪽이 다른 쪽을 포함하는가 — 박스오피스 등재 제목("인턴" vs "인턴: 확장판") 근사."""
        a = self.key
        b = other.key if isinstance(other, MovieTitle) else normalize_title(other)
        return bool(a) and bool(b) and (a in b or b in a)
