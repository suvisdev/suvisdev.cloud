"""소형 LLM의 JSON 응답에서 첫 번째로 완결되는 JSON 객체 하나만 추출한다.

소형 모델은 JSON 뒤에 부연설명을 덧붙이는 경우가 있어(EXAONE AWQ에서 실측), 첫 `{`부터
그리디하게 긁지 않는다. qwen_intent_classifier와 harvester 명령 파서가 공유한다.
"""

from __future__ import annotations

import json
from typing import Any


def extract_first_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = text.find("{")
    if start == -1:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
