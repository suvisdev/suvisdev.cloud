"""홈 포트폴리오 AI 채팅 회귀 하네스 — 범위 제한·근거 답변(2026-09-28).

- 범위 밖 질문(날씨·요리·코딩 대행·시사)은 고정 거절 문구로 답해야 한다.
- 진수택·프로젝트 질문은 거절하지 않고, 핵심 단어가 답에 들어가야 한다(ARDA는 지킬 근거).

Usage (suvisdev 폴더에서):
  python scripts/eval_portfolio_chat.py --base-url http://127.0.0.1:31386   # 노트북 NodePort
"""

from __future__ import annotations

import argparse
import json
import time

import httpx

_DEFAULT_BASE_URL = "https://api.suvisdev.cloud"
_REFUSAL = "질문에만 답하고 있어요"

CASES: list[dict[str, object]] = [
    {"q": "진수택은 어떤 개발자야", "scope": True, "must": ["진수택"]},
    {"q": "학력이 어떻게 돼", "scope": True, "must": ["경상대"]},
    {"q": "mova는 뭐야", "scope": True, "must": ["영화"]},
    {"q": "길들은 뭐야", "scope": True, "must": ["산책"]},
    {"q": "ARDA 기술 스택 알려줘", "scope": True, "must": ["FastAPI"]},
    {"q": "안녕 너는 누구야", "scope": True, "must": ["Suvisdev"]},
    {"q": "오늘 날씨 어때", "scope": False},
    {"q": "파이썬으로 퀵소트 짜줘", "scope": False},
    {"q": "김치찌개 레시피 알려줘", "scope": False},
    {"q": "대한민국 대통령은 누구야", "scope": False},
    {"q": "비트코인 전망은?", "scope": False},
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    passed = 0
    for i, case in enumerate(CASES, 1):
        try:
            r = httpx.post(
                f"{args.base_url}/portfolio/chat", json={"message": case["q"]}, timeout=120.0
            )
            r.raise_for_status()
            reply = r.json().get("reply") or ""
        except httpx.HTTPError as e:
            print(f"[{i}/{len(CASES)}] ERROR | {case['q']} | {e}", flush=True)
            continue
        refused = _REFUSAL in reply
        problems = []
        if case["scope"] and refused:
            problems.append("범위 안인데 거절")
        if not case["scope"] and not refused:
            problems.append("범위 밖인데 답함")
        for word in case.get("must", []):  # type: ignore[union-attr]
            if word not in reply:
                problems.append(f"'{word}' 없음")
        ok = not problems
        passed += ok
        print(
            f"[{i}/{len(CASES)}] {'PASS' if ok else 'FAIL'} | {case['q']} | {reply[:60].replace(chr(10), ' ')}"
            + (f" | {'; '.join(problems)}" if problems else ""),
            flush=True,
        )
        time.sleep(args.sleep)
    print(f"\n결과: {passed}/{len(CASES)} PASS")
    print(json.dumps({"passed": passed, "total": len(CASES)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
