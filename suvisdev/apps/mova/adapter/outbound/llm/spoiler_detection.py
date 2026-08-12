"""리뷰 본문에서 스포일러 후보 문구를 뽑아 인덱스 스팬으로 반환한다.

Gemini에 리뷰 텍스트를 보내 "스포일러가 될 만한 짧은 문구"만 JSON 리스트로
받고, body에서 실제 위치를 find()로 잡아 스팬으로 변환한다. 검출 실패·쿼터
초과 등 어떤 예외도 상위 리뷰 저장 자체를 막지 않는다(빈 리스트 반환).
"""

from __future__ import annotations

import json
import logging
import re

from mova.adapter.outbound.llm.gemini_client import gemini_reply

logger = logging.getLogger(__name__)

_SPOILER_SYSTEM = (
    "너는 영화 리뷰에서 스포일러가 될 만한 짧은 문구를 찾는 도우미다. "
    "규칙:\n"
    "1) 결말, 반전, 캐릭터의 죽음/생존, 정체·비밀 공개, 중요한 사건의 결과처럼 "
    "   작품을 아직 안 본 사람의 감상을 망칠 만한 문구만 뽑는다.\n"
    "2) 일반적인 감상(재밌다·연기가 좋다·명작이다)이나 장르·분위기 언급은 스포일러가 아니다.\n"
    "3) 뽑은 문구는 리뷰 원문에 그대로 있는 부분 문자열이어야 한다(요약·재구성 금지).\n"
    "4) 각 문구는 최대 40자 이내로 짧게. 문장 전체를 통째로 가리지 말고 핵심만.\n"
    '5) 없으면 빈 배열. 응답은 반드시 JSON 객체 {"spoilers": ["문구1", "문구2", ...]} '
    "형식 하나만 반환한다(설명·주석 없이)."
)


def _parse_spoiler_phrases(raw: str) -> list[str]:
    """모델 응답에서 phrase 리스트만 뽑아낸다. 코드펜스·앞뒤 잡음에 관대하게."""
    text = raw.strip()
    if not text:
        return []
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    raw_list = data.get("spoilers") if isinstance(data, dict) else data
    if not isinstance(raw_list, list):
        return []
    out: list[str] = []
    for item in raw_list:
        if isinstance(item, str):
            s = item.strip()
            if s and len(s) <= 40:
                out.append(s)
    return out


def _to_spans(body: str, phrases: list[str]) -> list[dict]:
    """phrase 리스트를 body에서 실제 위치로 매핑. 중복·겹침은 정리."""
    spans: list[dict] = []
    seen_ranges: list[tuple[int, int]] = []
    for phrase in phrases:
        if not phrase:
            continue
        # 첫 등장만 잡는다 — 같은 문구가 여러 번 있으면 첫 것만.
        idx = body.find(phrase)
        if idx == -1:
            continue
        end = idx + len(phrase)
        # 이미 커버된 범위와 겹치면 스킵
        if any(not (end <= s or idx >= e) for s, e in seen_ranges):
            continue
        seen_ranges.append((idx, end))
        spans.append({"start": idx, "end": end, "text": phrase})
    # start 순 정렬 — 프런트 렌더가 순차적으로 자른다
    spans.sort(key=lambda s: s["start"])
    return spans


def detect_spoiler_spans(body: str) -> list[dict]:
    """리뷰 본문에서 스포일러 스팬 리스트를 반환. 실패해도 [] 반환."""
    text = (body or "").strip()
    if not text or len(text) < 8:
        return []
    prompt = f"{_SPOILER_SYSTEM}\n\n리뷰 본문:\n---\n{text}\n---"
    try:
        raw = gemini_reply(prompt, model_key="flash15")
    except Exception as e:  # 쿼터·네트워크·SDK 예외 등 다 삼킴
        logger.info("[spoiler] gemini_reply 실패: %s", e)
        return []
    phrases = _parse_spoiler_phrases(raw)
    return _to_spans(text, phrases)
