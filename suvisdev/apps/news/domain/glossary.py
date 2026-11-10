"""용어 정리 — 글에 나오는 전문 용어를 검수한 사전(glossary.json)에서 찾아 준다 (2026-11-06, 외부 의존 없음).

모델이 뜻을 쓰게 하지 않는다. 11-06 EXAONE 7.8B 시험: 글당 15초(요약만 하면 3초), '역기구학'을 정기구학 뜻으로,
'MiMo V2.6'(샤오미 모델)을 통신 기술 MIMO 로 설명했고, '하락'·'마감' 같은 흔한 말을 골랐다. 공부용 화면에서 틀린 뜻은
치명적이라 미리 써 둔 고정 사전만 쓴다. 대신 사전에 없는 새 용어는 나오지 않는다 — glossary.json 에 한 줄 더하면 된다.
영어 'attention'(주목)·'alignment'(구조 정렬)처럼 일상 뜻이 따로 있는 말은 기술 용어로 쓰인 꼴만 사전에 넣는다.

찾는 규칙 (오탐 방지)
- 영문 대문자 약어(RAG, MoE, PER)는 대소문자까지 같아야 한다 — "storage" 의 rag, "per" 를 잡지 않게
- 그 밖의 영문은 대소문자 무시, 단어 경계 필수 — "attention" 은 잡고 "reattention" 은 안 잡는다
- 한글은 그대로 포함되면 잡는다(조사가 붙으므로). 섹션이 맞는 글에서만 찾는다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MAX_TERMS_PER_ARTICLE = 4
_PATH = Path(__file__).resolve().parent / "glossary.json"
_ASCII = re.compile(r"^[\x00-\x7f]+$")


@dataclass(frozen=True)
class GlossaryTerm:
    term: str
    desc: str


@dataclass(frozen=True)
class _Entry:
    term: str
    desc: str
    section: str
    pattern: re.Pattern[str]


def _alias_pattern(alias: str) -> str:
    body = re.escape(alias).replace(r"\ ", r"[\s-]+")
    if not _ASCII.match(alias):
        return body
    # 영문·숫자에 붙은 경우는 다른 단어다("attention" ≠ "reattention"). 한글 조사가 바로 붙는 건 허용한다.
    return rf"(?<![0-9A-Za-z]){body}(?![0-9A-Za-z])"


def _is_case_sensitive(alias: str) -> bool:
    """대문자가 둘 이상인 영문 약어(RAG, MoE, GNN, F4)는 대소문자를 구분한다."""
    return bool(_ASCII.match(alias)) and sum(ch.isupper() for ch in alias) >= 2 and " " not in alias


def _compile(aliases: list[str]) -> re.Pattern[str]:
    parts = [
        _alias_pattern(a) if _is_case_sensitive(a) else f"(?i:{_alias_pattern(a)})"
        for a in sorted(aliases, key=len, reverse=True)
    ]
    return re.compile("|".join(parts))


@lru_cache(maxsize=1)
def _entries() -> tuple[_Entry, ...]:
    raw: list[dict[str, object]] = json.loads(_PATH.read_text(encoding="utf-8"))
    out: list[_Entry] = []
    for item in raw:
        aliases = item["match"]
        if not isinstance(aliases, list):
            raise ValueError(f"glossary.json: {item['term']} 의 match 가 목록이 아님")
        out.append(
            _Entry(
                term=str(item["term"]),
                desc=str(item["desc"]),
                section=str(item["section"]),
                pattern=_compile([str(a) for a in aliases]),
            )
        )
    return tuple(out)


def find_terms(
    text: str, section: str, limit: int = MAX_TERMS_PER_ARTICLE
) -> tuple[GlossaryTerm, ...]:
    """글(text)에 나오는 사전 용어를 먼저 나온 순서로 limit 개까지. section 이 맞는 항목만 본다."""
    found: list[tuple[int, int, _Entry]] = []
    for entry in _entries():
        if entry.section not in (section, "both"):
            continue
        match = entry.pattern.search(text)
        if match:
            # 같은 자리면 더 긴 말(희소 어텐션 > 어텐션)을 앞세운다
            found.append((match.start(), -(match.end() - match.start()), entry))
    found.sort(key=lambda f: (f[0], f[1]))
    return tuple(GlossaryTerm(term=e.term, desc=e.desc) for _, _, e in found[:limit])
