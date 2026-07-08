from __future__ import annotations

import re

# 소형 로컬 모델(exaone3.5 등)은 프롬프트로 금지해도 대괄호 플레이스홀더·마크다운을
# 종종 남긴다. 시스템 프롬프트만으로는 신뢰할 수 없어 출력을 한 번 더 정리한다.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")
_PLACEHOLDER_RE = re.compile(r"\[[^\[\]\n]{1,40}\]")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
# 내용 없이 "****"처럼 남는 볼드 마커 — 위 _BOLD_RE는 내용이 있어야 매치되므로 별도 처리.
_STRAY_ASTERISKS_RE = re.compile(r"\*{2,}")


def sanitize_body(text: str) -> str:
    text = _PLACEHOLDER_RE.sub("", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _HEADER_RE.sub("", text)
    text = _STRAY_ASTERISKS_RE.sub("", text)
    lines = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in text.split("\n")]
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()
