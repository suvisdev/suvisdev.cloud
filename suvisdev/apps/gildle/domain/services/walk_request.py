"""산책 요청 이해 — 규칙 파서와 검증기(2026-09-28).

mova 오케스트레이터와 같은 구조다. 7.8B가 자연어("30분 동안 편하게 2키로 걷고 집에 올래")를
슬롯 JSON으로 이해하고, 이 모듈이 그 슬롯을 검증한다. 숫자·키워드는 문장에서 정규식으로 직접
뽑을 수 있으므로 문장에 근거가 있으면 규칙 쪽을 믿고, 모델은 규칙이 못 잡은 표현을 채운다.
모델이 죽어도 규칙만으로 같은 형태의 결과를 낸다. 경로 계산 자체는 여기서 하지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from gildle.domain.services.walk_preference import PREFERENCES

STOP_CATEGORIES = ("동물병원", "펫샵", "용품점", "애견카페")
MIN_MINUTES, MAX_MINUTES = 5, 180
MIN_KM, MAX_KM = 0.3, 15.0
WALK_SPEED_M_PER_S = 1.2  # 강아지와 걷는 평지 속도(라우터 ETA와 같은 값)
DEFAULT_MINUTES = 30

_PREF_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hilly", ("언덕", "오르막", "경사", "등산", "운동되", "운동 되", "운동이 되", "땀")),
    (
        "flat",
        ("편한", "편하게", "편히", "평지", "완만", "평평", "무릎", "노견", "힘들지 않", "쉬운"),
    ),
    ("shade", ("그늘", "햇빛", "햇볕", "덥", "시원")),
    ("green", ("나무", "숲", "공원", "푸른", "초록", "자연")),
    ("fast", ("빠른", "빨리", "최단", "짧은 길", "금방")),
)
_STOP_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("동물병원", ("동물병원", "병원", "진료", "예방접종")),
    ("펫샵", ("펫샵", "애견샵", "펫숍", "미용")),
    ("용품점", ("용품", "사료", "간식")),
    ("애견카페", ("애견카페", "강아지 카페", "카페")),
)
_KOREAN_NUM = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6}
# "동물병원으로 가는 최단 경로", "병원까지" — 조사 뒤에 이동·경로 단서가 붙으면 그 앞이 목적지(2026-09-29).
_DESTINATION = re.compile(
    r"([가-힣A-Za-z0-9 ]{1,24}?)\s*(?:으로|로|까지|에)\s*"
    r"(?:가는|가고|가자|갈래|갈까|가 ?줘|가야|걸어|향해|도착|최단|빠른|짧은|경로|길 ?좀|길 ?알려)"
)


@dataclass(frozen=True)
class WalkRequest:
    """이해 결과 — kind는 loop(출발지로 돌아옴) 또는 route(도착지까지)."""

    kind: str = "loop"
    minutes: int | None = None
    distance_km: float | None = None
    preference: str = "flat"
    stops: tuple[str, ...] = ()
    destination: str | None = None  # route일 때 목적지 종류(STOP_CATEGORIES) — 좌표는 코드가 고른다
    source: str = "rules"  # llm | rules | form
    notes: tuple[str, ...] = field(default_factory=tuple)

    def targets(self) -> tuple[float, float | None]:
        """(목표 길이 m, 상한 m). 시간만 주면 그 시간에 걸을 거리의 95%를 목표로, 상한은 그 거리.
        둘 다 주면 더 짧은 쪽을 목표로 삼고 시간은 상한으로 지킨다."""
        max_m = self.minutes * 60 * WALK_SPEED_M_PER_S if self.minutes else None
        if self.distance_km:
            target = self.distance_km * 1000
            return (min(target, max_m) if max_m else target), max_m
        if max_m:
            return max_m * 0.95, max_m
        default = DEFAULT_MINUTES * 60 * WALK_SPEED_M_PER_S
        return default * 0.95, default


def _minutes(text: str) -> int | None:
    t = text.replace(" ", "")
    total = 0.0
    found = False
    m = re.search(r"(\d+(?:\.\d+)?|한|두|세)시간(반)?", t)
    if m:
        n = m.group(1)
        total += (float(n) if n[0].isdigit() else _KOREAN_NUM[n]) * 60 + (30 if m.group(2) else 0)
        found = True
    m = re.search(r"(\d+)분", t)
    if m:
        total += int(m.group(1))
        found = True
    return int(total) if found else None


def _km(text: str) -> float | None:
    t = text.replace(" ", "").lower()
    m = re.search(r"(\d+(?:\.\d+)?)(km|㎞|키로|킬로)", t)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)(m|미터)(?![a-z])", t)
    if m and int(m.group(1)) >= 100:
        return int(m.group(1)) / 1000
    return None


def _preference(text: str) -> str | None:
    for pref, words in _PREF_WORDS:
        if any(w in text for w in words):
            return pref
    return None


def _stops(text: str) -> tuple[str, ...]:
    return tuple(cat for cat, words in _STOP_WORDS if any(w in text for w in words))


def _category_of(phrase: str) -> str | None:
    for cat, words in _STOP_WORDS:
        if any(w in phrase for w in words):
            return cat
    return None


def _destination(text: str) -> str | None:
    """목적지 종류. "집으로 돌아오는" 건 목적지가 아니고, 종류를 모르는 장소명은 아직 다루지 않는다."""
    for m in _DESTINATION.finditer(text or ""):
        phrase = m.group(1).strip()
        if "집" in phrase:
            continue
        cat = _category_of(phrase)
        if cat:
            return cat
    return None


def parse_rules(text: str) -> WalkRequest:
    """모델 없이 문장에서 바로 뽑는 규칙 이해 — 폴백이자 검증 근거."""
    t = text or ""
    destination = _destination(t)
    return WalkRequest(
        kind="route"
        if destination or (re.search(r"까지\s*(가|걸)", t) and "집" not in t)
        else "loop",
        minutes=_clamp_minutes(_minutes(t)),
        distance_km=_clamp_km(_km(t)),
        preference=_preference(t) or "flat",
        stops=tuple(s for s in _stops(t) if s != destination),
        destination=destination,
        source="rules",
    )


def _clamp_minutes(v: object) -> int | None:
    if isinstance(v, bool) or not isinstance(v, int | float) or v <= 0:
        return None
    return int(max(MIN_MINUTES, min(MAX_MINUTES, v)))


def _clamp_km(v: object) -> float | None:
    if isinstance(v, bool) or not isinstance(v, int | float) or v <= 0:
        return None
    return round(max(MIN_KM, min(MAX_KM, float(v))), 2)


def verify(llm: Mapping[str, object] | None, text: str) -> WalkRequest:
    """모델 슬롯을 검증해 규칙 결과와 합친다.

    - 숫자: 문장에서 규칙이 잡은 값이 있으면 그 값(문장이 근거). 없을 때만 모델 값을 범위 안으로.
    - 선호: 문장에 키워드 근거가 있으면 규칙, 없으면 모델 값이 목록 안일 때만.
    - 들를 곳: 규칙 ∪ 목록 안의 모델 값.
    - 목적지: 규칙이 잡았으면 규칙. 아니면 모델 값이 종류 목록 안이고 문장에 그 종류의 단어가 있을 때만
      (근거 없는 목적지는 버린다 — mova title 규칙과 같다). 목적지는 들를 곳에서 뺀다.
    """
    rules = parse_rules(text)
    if not llm:
        return rules
    notes: list[str] = []
    minutes = rules.minutes
    if minutes is None:
        minutes = _clamp_minutes(llm.get("minutes"))
    elif _clamp_minutes(llm.get("minutes")) not in (None, minutes):
        notes.append("minutes:rules")
    km = rules.distance_km
    if km is None:
        km = _clamp_km(llm.get("distance_km"))
    elif _clamp_km(llm.get("distance_km")) not in (None, km):
        notes.append("distance:rules")
    llm_pref = llm.get("preference")
    keyword_pref = _preference(text)
    if keyword_pref:
        pref = keyword_pref
        if llm_pref in PREFERENCES and llm_pref != keyword_pref:
            notes.append("preference:rules")
    elif isinstance(llm_pref, str) and llm_pref in PREFERENCES:
        pref = llm_pref
    else:
        pref = rules.preference
    raw_stops = llm.get("stops")
    llm_stops = (
        [s for s in raw_stops if isinstance(s, str) and s in STOP_CATEGORIES]
        if isinstance(raw_stops, list)
        else []
    )
    destination = rules.destination
    llm_dest = llm.get("destination")
    if (
        destination is None
        and isinstance(llm_dest, str)
        and llm_dest in STOP_CATEGORIES
        and llm_dest in _stops(text)
    ):
        destination = llm_dest
    stops = tuple(
        c for c in STOP_CATEGORIES if (c in rules.stops or c in llm_stops) and c != destination
    )
    if destination:
        kind = "route"
    else:
        kind = llm.get("kind") if llm.get("kind") in ("loop", "route") else rules.kind
    return WalkRequest(
        kind=str(kind),
        minutes=minutes,
        distance_km=km,
        preference=pref,
        stops=stops,
        destination=destination,
        source="llm",
        notes=tuple(notes),
    )


def apply_form(
    base: WalkRequest,
    *,
    minutes: int | None,
    distance_km: float | None,
    preference: str | None,
    stops: list[str] | None,
    has_end: bool,
    has_text: bool,
) -> WalkRequest:
    """화면에서 직접 고른 값은 이해 결과보다 우선한다(사용자가 명시한 것).
    지도에서 도착지를 찍었으면(has_end) 그 좌표가 목적지라 문장의 목적지 종류는 쓰지 않는다."""
    return WalkRequest(
        kind="route" if has_end or base.destination else "loop",
        minutes=_clamp_minutes(minutes) if minutes else base.minutes,
        distance_km=_clamp_km(distance_km) if distance_km else base.distance_km,
        preference=preference if preference in PREFERENCES else base.preference,
        stops=tuple(s for s in STOP_CATEGORIES if s in (stops or [])) or base.stops,
        destination=None if has_end else base.destination,
        source=base.source if has_text else "form",
        notes=base.notes,
    )
