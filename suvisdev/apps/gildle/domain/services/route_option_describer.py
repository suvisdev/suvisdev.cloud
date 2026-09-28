"""경로 후보의 "이 길을 고를 이유" 문장 — 수치로만 만든다(지어내지 않음). 2026-09-28.

후보 종류: fast(빠른 길) · shade(그늘 많은 길) · green(푸른 길) · via(장소 들렀다 가기).
외부 의존이 없는 순수 규칙이라 도메인 서비스로 둔다. 나중에 LLM이 문장을 다듬더라도 근거 수치는
여기서 만든 값만 쓴다.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

WALK_SPEED_MPS = 1.2  # 앱·웹 표시와 동일

KIND_LABEL = {
    "fast": "빠른 길",
    "shade": "그늘 많은 길",
    "green": "푸른 길",
    "flat": "편한 길",
    "hilly": "언덕길",
    "via": "들렀다 가는 길",
}


@dataclass(frozen=True)
class RouteOptionMetrics:
    length_m: float
    shade_ratio: float | None  # 낮 시간에만(밤·데이터 없음이면 None)
    green_ratio: float  # 길이가중 수관 점수 0~1
    roads: tuple[str, ...] = ()
    place_categories: tuple[str, ...] = ()  # 경로 곁 장소 카테고리(중복 포함)
    via_name: str | None = None
    climb_m: float | None = None  # 누적 오르막(SRTM 고도가 있을 때)
    loop_target_m: float | None = None  # 집으로 돌아오는 루프면 목표 거리

    @property
    def minutes(self) -> int:
        return max(1, round(self.length_m / WALK_SPEED_MPS / 60))


@dataclass(frozen=True)
class RouteOptionText:
    label: str
    reason: str
    highlights: list[str] = field(default_factory=list)


def _eul_reul(word: str) -> str:
    """받침 있으면 '을', 없으면 '를'(한글이 아니면 '를')."""
    ch = word[-1:] if word else ""
    if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28:
        return "을"
    return "를"


def _pct(x: float) -> int:
    return round(x * 100)


def _km(m: float) -> str:
    return f"{m / 1000:.1f}km"


def describe(kind: str, m: RouteOptionMetrics, shortest_m: float) -> RouteOptionText:
    extra = max(0.0, m.length_m - shortest_m)
    extra_txt = "거의 같은 거리로" if extra < 40 else f"{round(extra)}m 더 걷지만"
    parts: list[str] = []
    highlights: list[str] = [f"{_km(m.length_m)} · 약 {m.minutes}분"]

    if m.loop_target_m:
        parts.append(
            f"목표 {_km(m.loop_target_m)}에 맞춰 출발지로 돌아오는 {KIND_LABEL.get(kind, '')} 코스예요."
        )
        if kind == "shade" and m.shade_ratio is not None:
            parts.append(f"그늘이 {_pct(m.shade_ratio)}%예요.")
        elif kind == "green":
            parts.append(f"나무·공원 구간이 {_pct(m.green_ratio)}%예요.")
        elif kind == "flat" and m.climb_m is not None:
            parts.append(f"오르막은 {round(m.climb_m)}m로 완만해요.")
        elif kind == "hilly" and m.climb_m is not None:
            parts.append(f"오르막 {round(m.climb_m)}m로 운동이 돼요.")
    elif kind == "fast":
        parts.append("가장 짧은 길이에요.")
    elif kind == "shade" and m.shade_ratio is not None:
        parts.append(f"{extra_txt} 그늘이 {_pct(m.shade_ratio)}%로 햇볕을 가장 덜 받아요.")
    elif kind == "green":
        parts.append(f"{extra_txt} 나무·공원 구간이 {_pct(m.green_ratio)}%로 가장 푸른 길이에요.")
    elif kind == "flat" and m.climb_m is not None:
        parts.append(f"{extra_txt} 오르막이 {round(m.climb_m)}m로 가장 편하게 걸을 수 있어요.")
    elif kind == "hilly" and m.climb_m is not None:
        parts.append(f"오르막이 {round(m.climb_m)}m 있는 언덕길이라 운동이 돼요.")
    elif kind == "via" and m.via_name:
        parts.append(
            f"『{m.via_name}』에 들렀다 가는 길이에요"
            + (f"(바로 가는 길보다 {round(extra)}m 더)." if extra >= 40 else ".")
        )

    if m.shade_ratio is not None:
        highlights.append(f"그늘 {_pct(m.shade_ratio)}%")
    highlights.append(f"나무 {_pct(m.green_ratio)}%")
    if m.climb_m is not None:
        highlights.append(f"오르막 {round(m.climb_m)}m")
    if m.roads:
        joined = "·".join(m.roads)
        parts.append(f"주로 {joined}{_eul_reul(joined)} 지나요.")
    if m.place_categories:
        counts = Counter(m.place_categories)
        listed = "·".join(f"{c} {n}곳" for c, n in counts.most_common())
        parts.append(f"가는 길에 {listed}이 있어요.")
        highlights.append(f"반려동물 장소 {sum(counts.values())}곳")
    return RouteOptionText(
        label=KIND_LABEL.get(kind, kind), reason=" ".join(parts), highlights=highlights
    )
