"""규칙 레이어 판정 (newsdesk 하네스 rubric.md §3 결정표).

모드는 세 모델 비교를 그대로 따른다.
  A = 제목만, B = 제목 + 요약·본문, C = 제목 + 요약·본문 + 출처(도메인, 교차 보도)
앱은 C 를 쓴다. A·B 는 하네스 evaluate.py 가 비교용으로 돌린다.
이 파일은 suvisdev.cloud 저장소 apps/news/domain/ai_filter/ 와 newsdesk 하네스 scripts/ai_filter/ 에 같은 내용으로 있다.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from .signals import REASON_KO, Article, Metrics, Signal, article_signals, batch_signals

_HERE = Path(__file__).resolve().parent
MODES = {"A": (False, False), "B": (True, False), "C": (True, True)}


@lru_cache(maxsize=1)
def load_thresholds() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_HERE / "thresholds.json").read_text(encoding="utf-8"))
    return data


@lru_cache(maxsize=1)
def load_sources() -> dict[str, list[str]]:
    data: dict[str, list[str]] = json.loads((_HERE / "sources.json").read_text(encoding="utf-8"))
    return data


def decide(
    sigs: Sequence[Signal], metrics: Metrics, th: Mapping[str, Any], mode: str
) -> tuple[str, dict[str, Any]]:
    codes = {s["code"] for s in sigs}
    strong = [s for s in sigs if s["strength"] == "strong"]

    ai_pts = sum(int(th["ai_trace_points"].get(c, 0)) for c in codes)  # 같은 코드는 한 번만 센다
    ai_fail = ai_pts >= th["ai_trace_fail_at"]
    # 교차 보도는 미확인 출처를 상쇄한다. 단 남의 기사를 재가공한 의심이 있으면 상쇄하지 않는다.
    src_fail = "UNKNOWN_SOURCE" in codes and not (
        "CROSSCHECKED" in codes and "REWRITE_SUSPECT" not in codes
    )
    ev_fail = "NO_EVIDENCE" in codes

    body_chars = int(metrics.get("body_chars", 0))
    source_axis = "n/a"
    if mode == "C":
        source_axis = "blocked" if "BLOCKED_SOURCE" in codes else "unknown" if src_fail else "ok"
    axes: dict[str, Any] = {
        "ai_trace": ai_pts if body_chars > 0 else "n/a",
        "source": source_axis,
        "evidence": ("none" if ev_fail else "ok")
        if body_chars >= th["min_body_chars_for_evidence"]
        else "n/a",
        "style": sorted(c for c in codes if c in ("CLICKBAIT", "TITLE_BODY_MISMATCH")),
    }

    if strong:
        return "ai", axes
    if ai_fail and (src_fail or ev_fail):
        return "ai", axes
    if ai_fail or (src_fail and ev_fail):
        return "pending", axes
    return "normal", axes


def badge_of(verdict: str, sigs: Sequence[Signal], axes: Mapping[str, Any]) -> dict[str, Any]:
    """화면 배지 (rubric.md §0). 숨기지 않고 표시만 한다. pending 은 2차 판정 전까지 배지 없음."""
    codes = [s["code"] for s in sigs]
    if verdict != "ai":
        return {"badge": "none", "reasons_ko": []}
    reasons = [
        REASON_KO[c]
        for c in codes
        if c in REASON_KO and not (c == "UNKNOWN_SOURCE" and axes["source"] != "unknown")
    ]
    badge = "ai_disclosed" if "AI_DISCLOSURE" in codes else "ai_suspected"
    return {"badge": badge, "reasons_ko": reasons}


def classify(
    articles: Sequence[Article],
    mode: str = "C",
    sources: Mapping[str, Sequence[str]] | None = None,
    th: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """기사 여러 건을 한 번에 판정한다. 교차 보도·재가공 신호는 같은 배치 안에서만 계산된다."""
    th = th if th is not None else load_thresholds()
    sources = sources if sources is not None else load_sources()
    use_body, use_source = MODES[mode]

    per: dict[str, dict[str, Any]] = {}
    for a in articles:
        if "id" not in a:
            raise ValueError(f"id 없는 기사: {str(a)[:80]}")
        sigs, m = article_signals(a, th, sources, use_body=use_body, use_source=use_source)
        per[str(a["id"])] = {"signals": sigs, "metrics": m}
    if use_source and len(articles) > 1:
        batch_signals(articles, per, th, sources)

    out: list[dict[str, Any]] = []
    for a in articles:
        p = per[str(a["id"])]
        # 같은 코드 중복 제거 (재가공 신호는 짝마다 붙을 수 있다)
        seen: set[str] = set()
        uniq: list[Signal] = []
        for s in p["signals"]:
            if s["code"] not in seen:
                seen.add(s["code"])
                uniq.append(s)
        verdict, axes = decide(uniq, p["metrics"], th, mode)
        out.append(
            {
                "id": a["id"],
                "verdict": verdict,
                **badge_of(verdict, uniq, axes),
                "layer": "rules",
                "mode": mode,
                "harness_version": th["harness_version"],
                "axes": axes,
                "signals": uniq,
                "metrics": p["metrics"],
            }
        )
    return out
