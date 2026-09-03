"""mova 채팅 고정 평가셋 회귀 하네스 — 프로덕션(또는 로컬) 실호출 비교.

사고 이력 질의 + 교사 데이터셋 스킵 질의를 고정 세트로 돌려, 수정·재학습·배포
후 회귀를 잡는다(2026-09-03 신설, 품질 주력 방향의 3번 항목). 판정은 결정론
규칙만 쓴다 — recs 유무, 연도 하드 조건 위반, 금지 픽(과거 실사고의 무관 픽).

Usage (suvisdev 폴더에서):
  python scripts/eval_chat_queries.py                 # 프로덕션
  python scripts/eval_chat_queries.py --base-url http://127.0.0.1:8000
  python scripts/eval_chat_queries.py --only 좀비     # 질의 부분 문자열 필터

레이트리밋(IP당 20회/60s)을 고려해 질의 사이에 짧게 쉰다.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

import httpx

_DEFAULT_BASE_URL = "https://api.suvisdev.cloud"

# spec 키: q(질의) · min_recs(기본 1) · max_recs(기본 없음, 인사말은 0)
#          year_max/year_min(추천작 연도 하드 조건) · banned(제목 부분 문자열)
#          note(왜 세트에 있는가 — 사고·스킵 출처)
SPECS: list[dict[str, Any]] = [
    # --- 실사고 이력 (재발 방지) ---
    {"q": "좀비 영화 추천해줘", "note": "9/2 필러 '좀→비' 오염"},
    {"q": "타임루프 소재 영화 추천해줘", "note": "9/1 스킵→키워드 태그로 부활"},
    {"q": "일본 애니메이션 영화 추천", "note": "8/26 언어 허용목록 과차단"},
    {
        "q": "클래식 명작 처음 보는 사람용",
        "year_max": 1999,
        "banned": ["식객"],
        "note": "9/3 RAG 연도 재검증(식객 무관 픽)",
    },
    {"q": "최신영화 알려줘", "year_min": 2024, "note": "9/2 booking 오분류 + 연도 폴백 합류"},
    {"q": "안녕", "min_recs": 0, "max_recs": 0, "note": "no-pick 인사말 — 카드 없이 안내"},
    # --- 교사 데이터셋 스킵 17건 (9/2 재생성 기준) ---
    {"q": "한국 액션 영화 추천", "note": "스킵: catalog empty"},
    {"q": "역사 배경 한국 영화", "note": "스킵: catalog empty"},
    {
        "q": "2000년대 초반 한국 영화",
        "year_min": 2000,
        "year_max": 2009,
        "note": "스킵: catalog empty",
    },
    {"q": "송강호 나오는 영화", "note": "스킵: 배우 그라운딩"},
    {"q": "마동석 액션 영화", "note": "스킵: 배우 그라운딩"},
    {"q": "톰 크루즈 영화 추천", "note": "스킵: 배우 그라운딩"},
    {"q": "법정 드라마 영화", "note": "스킵: no grounded picks"},
    {"q": "조선시대 사극 영화", "note": "스킵: no grounded picks"},
    {"q": "정치 스릴러 영화", "note": "스킵: no grounded picks"},
    {"q": "형사물 추천해줘", "note": "스킵: no grounded picks — 9/3 라이브 정상 확인"},
    {"q": "밀실 탈출 스릴러", "note": "스킵: no grounded picks"},
    {"q": "심리전 두뇌 싸움 영화", "note": "스킵: no grounded picks"},
    {"q": "복수극 영화 추천", "note": "스킵: no grounded picks"},
    {"q": "유럽 배경 로맨스", "note": "스킵: no grounded picks"},
    {"q": "뉴욕 배경 영화", "note": "스킵: no grounded picks"},
    {"q": "춤 나오는 영화", "note": "스킵: no grounded picks"},
    {"q": "직장인 공감 영화", "note": "스킵: no grounded picks"},
]


def _year_of(rec: dict[str, Any]) -> int | None:
    try:
        return int(str(rec.get("year", "")).strip()[:4])
    except (TypeError, ValueError):
        return None


def _evaluate(spec: dict[str, Any], recs: list[dict[str, Any]]) -> list[str]:
    """위반 사유 목록을 돌려준다(빈 리스트 = PASS)."""
    problems: list[str] = []
    min_recs = spec.get("min_recs", 1)
    max_recs = spec.get("max_recs")
    if len(recs) < min_recs:
        problems.append(f"recs {len(recs)} < {min_recs}")
    if max_recs is not None and len(recs) > max_recs:
        problems.append(f"recs {len(recs)} > {max_recs}")
    for rec in recs:
        title = str(rec.get("title", ""))
        year = _year_of(rec)
        if spec.get("year_max") is not None and year and year > spec["year_max"]:
            problems.append(f"연도 위반: {title}({year}) > {spec['year_max']}")
        if spec.get("year_min") is not None and year and year < spec["year_min"]:
            problems.append(f"연도 위반: {title}({year}) < {spec['year_min']}")
        for banned in spec.get("banned", []):
            if banned in title:
                problems.append(f"금지 픽: {title}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    parser.add_argument("--only", default=None, help="질의 부분 문자열 필터")
    parser.add_argument("--sleep", type=float, default=2.0)
    args = parser.parse_args()

    specs = [s for s in SPECS if not args.only or args.only in s["q"]]
    passed = 0
    failures: list[tuple[str, list[str], list[str]]] = []

    for i, spec in enumerate(specs):
        try:
            r = httpx.post(
                f"{args.base_url}/mova/chat",
                json={"message": spec["q"]},
                timeout=90.0,
            )
            r.raise_for_status()
            data = r.json()
            recs = data.get("recommendations") or []
        except httpx.HTTPError as e:
            failures.append((spec["q"], [f"HTTP 오류: {e}"], []))
            print(f"[{i + 1}/{len(specs)}] ERROR | {spec['q']} | {e}", flush=True)
            time.sleep(args.sleep)
            continue

        titles = [f"{x.get('title')}({x.get('year')})" for x in recs]
        problems = _evaluate(spec, recs)
        status = "PASS" if not problems else "FAIL"
        if problems:
            failures.append((spec["q"], problems, titles))
        else:
            passed += 1
        print(
            f"[{i + 1}/{len(specs)}] {status} | {spec['q']} | {', '.join(titles) or '(0건)'}"
            + (f" | {'; '.join(problems)}" if problems else ""),
            flush=True,
        )
        time.sleep(args.sleep)

    print(f"\n결과: {passed}/{len(specs)} PASS")
    for q, problems, titles in failures:
        print(f"  FAIL {q}: {'; '.join(problems)} | picks={titles}")
    print(json.dumps({"passed": passed, "total": len(specs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
