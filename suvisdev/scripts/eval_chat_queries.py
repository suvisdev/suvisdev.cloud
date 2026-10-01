"""mova 채팅 고정 평가셋 회귀 하네스 — 프로덕션(또는 로컬) 실호출 비교.

사고 이력 질의 + 교사 데이터셋 스킵 질의를 고정 세트로 돌려, 수정·재학습·배포
후 회귀를 잡는다(2026-09-03 신설, 품질 주력 방향의 3번 항목). 판정은 결정론
규칙만 쓴다 — recs 유무, 연도 하드 조건 위반, 금지 픽(과거 실사고의 무관 픽).

Usage (suvisdev 폴더에서):
  python scripts/eval_chat_queries.py                 # 프로덕션
  python scripts/eval_chat_queries.py --base-url http://127.0.0.1:8000
  python scripts/eval_chat_queries.py --only 좀비     # 질의 부분 문자열 필터
  python scripts/eval_chat_queries.py --catalog ~/datasets/movielens/catalog.tsv --save before.json

카드 품질 지표(2026-09-28, 추천 기준 `apps/mova/_docs/MOVA_RECOMMENDATION_CRITERIA.md` §5)는
PASS/FAIL과 별개로 집계한다 — 투표 30건 미만 카드, 같은 시리즈 중복, 볼 수 있는 곳 있음,
질의 단어가 제목에 겹치는 카드(표면 매칭 의심, 사람이 확인). 투표 수는 --catalog(TSV: slug,
title, year, vote_count — 운영 DB에서 추출)가 있을 때만 센다.

레이트리밋(IP당 20회/60s)을 고려해 질의 사이에 짧게 쉰다.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
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
    {
        "q": "송강호 나오는 영화",
        # 09-22 DB 실측: 송강호는 두 작품 모두 미출연 — 배우 매칭이 1위를 잡아도
        # 뒤에 붙는 RAG 꼬리를 LoRA가 고르면 이런 픽이 나온다.
        "banned": ["천년여우", "궁합"],
        "note": "스킵: 배우 그라운딩",
    },
    {"q": "마동석 액션 영화", "note": "스킵: 배우 그라운딩"},
    {
        "q": "톰 크루즈 영화 추천",
        # 2026-09-22: 배우 미인식 시 제목에 "크루즈"가 든 영화가 후보를 채운다
        # (정규식 `_guess_actors`가 조사 없는 발화를 놓쳤다 → DB 실명 매칭으로 수정).
        "banned": ["정글 크루즈", "크루즈 패밀리"],
        "note": "스킵: 배우 그라운딩 + 09-22 무관 픽 재발 방지",
    },
    {
        "q": "법정 드라마 영화",
        "note": "카탈로그 갭(09-27: LoRA·Gemini 모두 0편, 후보 16편에 법정물 없음) — 실패는 데이터 문제",
    },
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
    # --- 분위기 질의 (09-28 추천 기준 작업 — 실사용 대화 38·40에서 품질이 약했던 유형) ---
    {
        "q": "비 오는 날 어울리는 영화",
        "note": "09-28 대화 38 — 제목 '날' 표면 매칭 의심(바람피기 좋은 날)",
    },
    {"q": "여행 가기 전에 보기 좋은 영화", "note": "09-28 대화 40"},
    {"q": "기분 좋아지는 영화", "note": "09-28 추천 기준 — 분위기"},
    {"q": "잔잔한 영화 추천해줘", "note": "09-28 추천 기준 — 분위기"},
    {"q": "소름 돋는 반전 영화", "note": "09-28 추천 기준 — 분위기"},
]

_LOW_VOTES = 30
# 서로 다른 질의 N개 이상에 같은 작품이 나오면 "조건과 무관한 채움" 의심(09-28 기준선: 분위기
# 질의 4개에 캔터빌의 유령·캠프 락 3·마운틴헤드가 반복 — 기존 지표로는 전부 PASS였다)
_REPEAT_QUERIES = 3
# 제목 겹침 판정에서 빼는 일반어 — 질의에 흔하지만 작품을 가리키지 않는 말
_GENERIC_WORDS = frozenset(
    "영화 추천 추천해줘 알려줘 어울리는 좋은 보기 나오는 배경 소재 전에 가기 사람용 처음 보는".split()
)
_SEQUEL_TAIL = re.compile(r"\s+(?:\d+|[IVX]+|시즌\s*\d+|part\s*\d+)$", re.IGNORECASE)


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


def _series_key(title: str) -> str:
    """'스파이더맨: 브랜드 뉴 데이'·'스파이더맨 2' → '스파이더맨'(부제·번호 제거)."""
    # 앱의 mova.domain.value_objects.movie_title.series_key와 같은 규칙(스크립트는 앱 import 없이 돈다)
    base = re.split(r"[:：]", title, maxsplit=1)[0].strip()
    return _SEQUEL_TAIL.sub("", base).strip() or title


def _words(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣]+", text)


def _query_words(q: str) -> set[str]:
    return {w for w in _words(q) if w not in _GENERIC_WORDS}


def _quality_metrics(
    q: str, recs: list[dict[str, Any]], votes: dict[str, int] | None
) -> dict[str, Any]:
    titles = [str(r.get("title", "")) for r in recs]
    keys = [_series_key(t) for t in titles]
    words = _query_words(q)
    m: dict[str, Any] = {
        "cards": len(recs),
        "series_dup": len(keys) != len(set(keys)),
        "available": sum(1 for r in recs if r.get("platform")),
        # 어절 단위로 같은 말이 있을 때만 — '비'가 '비와'에 걸리는 부분 문자열 오탐 방지
        "title_overlap": [t for t in titles if words & set(_words(t))],
    }
    if votes is not None:
        m["low_votes"] = [
            t
            for r, t in zip(recs, titles, strict=True)
            if votes.get(str(r.get("id")), 0) < _LOW_VOTES
        ]
    return m


def _load_votes(path: Path) -> dict[str, int]:
    votes: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[3].isdigit():
            votes[parts[0]] = int(parts[3])
    return votes


def _print_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ms = [r["metrics"] for r in rows]
    cards = sum(m["cards"] for m in ms)
    summary: dict[str, Any] = {
        "queries": len(ms),
        "cards": cards,
        "zero_card_queries": sum(1 for m in ms if m["cards"] == 0),
        "series_dup_queries": sum(1 for m in ms if m["series_dup"]),
        "available_cards": sum(m["available"] for m in ms),
        "title_overlap_cards": sum(len(m["title_overlap"]) for m in ms),
    }
    if ms and "low_votes" in ms[0]:
        summary["low_vote_cards"] = sum(len(m["low_votes"]) for m in ms)
    seen: dict[str, set[str]] = {}
    for r in rows:
        for t in r["titles"]:
            seen.setdefault(t, set()).add(r["q"])
    repeated = {t: sorted(qs) for t, qs in seen.items() if len(qs) >= _REPEAT_QUERIES}
    summary["repeated_titles"] = len(repeated)
    print("\n카드 품질 지표:")
    for k, v in summary.items():
        print(f"  {k:22} {v}")
    for r in rows:
        m = r["metrics"]
        notes = []
        if m["series_dup"]:
            notes.append("시리즈 중복")
        if m.get("low_votes"):
            notes.append(f"투표<{_LOW_VOTES}: {m['low_votes']}")
        if m["title_overlap"]:
            notes.append(f"제목 겹침: {m['title_overlap']}")
        if notes:
            print(f"  - {r['q']}: {' / '.join(notes)}")
    for t, qs in repeated.items():
        print(f"  - 반복 등장 {t}: {len(qs)}개 질의 {qs}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    parser.add_argument("--only", default=None, help="질의 부분 문자열 필터")
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument(
        "--catalog", type=Path, default=None, help="투표 수 TSV(slug·title·year·votes)"
    )
    parser.add_argument("--save", type=Path, default=None, help="질의별 카드·지표 JSON 저장")
    args = parser.parse_args()
    votes = _load_votes(args.catalog.expanduser()) if args.catalog else None
    rows: list[dict[str, Any]] = []

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
        metrics = _quality_metrics(spec["q"], recs, votes)
        rows.append(
            {"q": spec["q"], "titles": titles, "reply": data.get("reply") or "", "metrics": metrics}
        )
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
    summary = _print_quality(rows)
    if args.save:
        args.save.write_text(
            json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    print(json.dumps({"passed": passed, "total": len(specs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
