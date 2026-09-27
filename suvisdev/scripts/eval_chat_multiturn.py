"""mova 채팅 멀티턴·예매 문맥 회귀 하네스 — 실대화 로그(chat_messages)에서 뽑은 장면.

`eval_chat_queries.py`(23질의)는 전부 단일턴이라 "이전 대화를 기억 못하는" 실패를
하나도 못 잡았다(2026-09-22 실측: 대화 32·33·34). 여기는 history를 함께 보내
트랙 전환·상태 유지를 결정론 규칙으로 판정한다 — intent_type, 응답 문구 포함/금지,
추천 카드 제목. LoRA 출력이 아니라 히스토리를 다루는 코드를 겨냥한다.

Usage (suvisdev 폴더에서):
  python scripts/eval_chat_multiturn.py --base-url http://127.0.0.1:31386   # 노트북 NodePort
  python scripts/eval_chat_multiturn.py                                     # 프로덕션(터널)
  python scripts/eval_chat_multiturn.py --only 줄거리
장면을 추가할 땐 실제 대화 로그(chat_messages)의 문장을 그대로 쓴다.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

import httpx

_DEFAULT_BASE_URL = "https://api.suvisdev.cloud"
_REGION_ASK = "『옵세션』 상영관을 찾아드릴게요. 어느 지역에서 보실 계획인가요? 이동수단까지 알려주시면 더 정확해요"
_CHOICES = (
    "비슷한 제목이 여러 편이에요: 스파이더맨: 노 웨이 홈(2021) / 스파이더맨: 어크로스 더 유니버스(2023) / "
    "스파이더맨: 브랜드 뉴 데이(2026). 어떤 작품을 말씀하시나요?"
)

_INTERN_REGION_ASK = "『인턴』 상영관을 찾아드릴게요. 어느 지역에서 보실 계획인가요? 이동수단까지 알려주시면 더 정확해요"

SCENES: list[dict[str, Any]] = [
    # 09-27 대화 35 — 시간표 질의가 general로 새어 Gemini가 '롯데시네마 군자점 14:10·17:30'을 지어냄.
    {
        "name": "시간표 발화는 booking(인턴 영화 시간표 보여줘)",
        "history": [],
        "q": "인턴 영화 시간표 보여줘",
        "intent": "booking",
        "must": ["인턴"],
        "must_not": ["시 ", "회차가 있습니다"],
        "note": "대화 35 · 09-27 booking 어휘 선분기",
    },
    {
        "name": "시간표 대기 → 지역 답(군자)",
        "history": [
            {"role": "user", "content": "인턴 영화 시간표 보여줘"},
            {"role": "assistant", "content": _INTERN_REGION_ASK},
        ],
        "q": "군자",
        "intent": "booking",
        "must": ["군자"],
        "must_not": ["찾지 못했어요", "군자점"],
        "note": "대화 35 — 실제 극장 검색 결과여야 하고 '롯데시네마 군자점'은 존재하지 않는다",
    },
    {
        "name": "구어형 시간표(몇 시에 해?)도 booking — 회차를 지어내지 않는다",
        "history": [],
        "q": "인턴은 보통 몇 시간짜리야? 그리고 그거 몇 시에 해?",
        # 예매 어휘('몇 시')가 잡히면 booking, 아니면 general — 어느 쪽이든 회차를 지어내면 안 된다.
        "must_not": ["시 30분", "시 10분", "회차가 있습니다", "군자점"],
        "note": "09-27 general 프롬프트 실시간 사실 금지",
    },
    {
        "name": "체인 지점 질문은 booking(카카오 극장 검색)",
        "history": [],
        "q": "군자역 근처에 어느 체인 지점이 있는지 알려줘",
        "intent": "booking",
        "must_not": ["알 수 없", "군자점"],
        "note": "09-27 사용자 지적 — 극장 데이터가 있는데 잡담 트랙이 '모른다'고 답했다",
    },
    {
        "name": "구어형 시간표(몇 시에 볼 수 있어)도 booking",
        "history": [],
        "q": "군자에서 인턴 오늘 몇 시에 볼 수 있어?",
        "intent": "booking",
        "must": ["인턴"],
        "must_not": ["매칭되는 작품이 안 잡히네요", "군체", "감자"],
        "note": "09-27 라이브 확인 — 추천 트랙으로 새던 것",
    },
    {
        "name": "예매 대기 → 지역 답(군자역 근처)",
        "history": [
            {"role": "user", "content": "옵세션 예매하고싶어"},
            {"role": "assistant", "content": _REGION_ASK},
        ],
        "q": "군자역 근처",
        "intent": "booking",
        "must": ["군자"],
        "must_not": ["찾지 못했어요"],
        "note": "대화 34 · 09-22 낮 수정분",
    },
    {
        "name": "예매 대기 → 화제 전환(줄거리)",
        "history": [
            {"role": "user", "content": "옵세션 예매하고싶어"},
            {"role": "assistant", "content": _REGION_ASK},
        ],
        "q": "옵세션 줄거리 알려줘",
        # 여기서 잡으려는 건 "지역명으로 삼켜지지 않는가"다. 분류기(LLM)가 줄거리 요청을
        # evaluate 대신 recommend로 보내는 건 별개 결함(09-22 밤 실측)이라 트랙은 고정 안 함.
        "intent_not": "booking",
        "must_not": ["지역을 찾지 못했어요"],
        "note": "대화 34",
    },
    {
        "name": "제목 없는 예매(바로 예매할 수 있는 영화)",
        "history": [],
        "q": "바로 예매할 수 있는 영화 찾아줘",
        "intent": "booking",
        "must_not": ["비슷한 제목", "아바타"],
        "note": "대화 34 · '바로'가 제목 퍼지 매칭되던 오류",
    },
    {
        "name": "평가 직후 지역-선행 예매(군자쪽)",
        "history": [
            {"role": "user", "content": "옵세션 어때"},
            {
                "role": "assistant",
                "content": "음반점 직원 베어가 소꿉친구 니키의 사랑을 얻기 위해 소원을 빈 뒤 벌어지는 공포 이야기입니다.",
            },
        ],
        "q": "군자쪽에 예매할 시간 있는지 확인해줘",
        "intent": "booking",
        "must": ["군자"],
        "must_not": ["제목을 알려주시겠어요", "군체"],
        "note": "대화 33 · 평가 응답엔 제목이 없어 맥락을 못 잇던 오류",
    },
    {
        "name": "후보 제시 → 연도로 선택(26년꺼)",
        "history": [
            {"role": "user", "content": "스파이더맨 어때"},
            {"role": "assistant", "content": _CHOICES},
        ],
        "q": "26년꺼",
        "intent": "evaluate",
        "rec_title_contains": "브랜드 뉴 데이",
        "must_not": ["26년차"],
        "note": "대화 32",
    },
    {
        "name": "예매 대기 → 제목 없는 지역(강남)",
        "history": [
            {"role": "user", "content": "옵세션 예매하고싶어"},
            {"role": "assistant", "content": _REGION_ASK},
        ],
        "q": "강남",
        "intent": "booking",
        "must": ["강남"],
        "note": "화제 전환 방어의 오탐 확인(대조군)",
    },
]


def _evaluate(scene: dict[str, Any], data: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    reply = data.get("reply") or ""
    recs = data.get("recommendations") or []
    if scene.get("intent") and data.get("intent_type") != scene["intent"]:
        problems.append(f"intent {data.get('intent_type')} ≠ {scene['intent']}")
    if scene.get("intent_not") and data.get("intent_type") == scene["intent_not"]:
        problems.append(f"intent {data.get('intent_type')} 금지")
    for s in scene.get("must", []):
        if s not in reply:
            problems.append(f"응답에 '{s}' 없음")
    for s in scene.get("must_not", []):
        if s in reply:
            problems.append(f"응답에 '{s}' 포함")
    if scene.get("rec_title_contains"):
        if not any(scene["rec_title_contains"] in (r.get("title") or "") for r in recs):
            problems.append(f"카드에 '{scene['rec_title_contains']}' 없음")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    parser.add_argument("--only", default=None, help="장면 이름/질의 부분 문자열 필터")
    parser.add_argument("--sleep", type=float, default=2.0)
    args = parser.parse_args()

    scenes = [s for s in SCENES if not args.only or args.only in s["name"] or args.only in s["q"]]
    passed = 0
    failures: list[tuple[str, list[str], str]] = []
    for i, scene in enumerate(scenes):
        try:
            r = httpx.post(
                f"{args.base_url}/mova/chat",
                json={"message": scene["q"], "history": scene["history"]},
                timeout=90.0,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            failures.append((scene["name"], [f"HTTP 오류: {e}"], ""))
            print(f"[{i + 1}/{len(scenes)}] ERROR | {scene['name']} | {e}", flush=True)
            time.sleep(args.sleep)
            continue
        problems = _evaluate(scene, data)
        reply = (data.get("reply") or "").replace("\n", " ")[:80]
        status = "PASS" if not problems else "FAIL"
        if problems:
            failures.append((scene["name"], problems, reply))
        else:
            passed += 1
        print(
            f"[{i + 1}/{len(scenes)}] {status} | {scene['name']} | {data.get('intent_type')} | {reply}"
            + (f" | {'; '.join(problems)}" if problems else ""),
            flush=True,
        )
        time.sleep(args.sleep)

    print(f"\n결과: {passed}/{len(scenes)} PASS")
    for name, problems, reply in failures:
        print(f"  FAIL {name}: {'; '.join(problems)} | reply={reply}")
    print(json.dumps({"passed": passed, "total": len(scenes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
