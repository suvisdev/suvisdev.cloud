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
from pathlib import Path
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
        "name": "동명 작품은 상영 중인 쪽(인턴 2026)",
        "history": [],
        "q": "인턴 예매하고 싶어",
        "intent": "booking",
        "rec_title_contains": "인턴",
        "rec_year": 2026,
        "note": "09-27 사용자 지적 — 2015년작 카드가 나갔다(박스오피스 개봉연도로 선택)",
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
        # 오케스트레이터(09-27 저녁)는 작품+지역을 한 번에 읽어 되묻기 없이 극장 검색까지 간다 —
        # 응답 문구엔 제목이 없고 카드에 있다. 폴백 경로면 지역 되묻기 문구에 『인턴』이 있다.
        "rec_title_contains": "인턴",
        "must_not": ["매칭되는 작품이 안 잡히네요", "군체", "감자", "제목을 알려주시겠어요"],
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
    {
        "name": "예매 결과 → 날짜만 바꾼 후속(9월 30일자로)",
        "history": [
            {"role": "user", "content": "옵세션 예매하고싶어"},
            {"role": "assistant", "content": _REGION_ASK},
            {"role": "user", "content": "서울 전체로 찾아줘"},
            {
                "role": "assistant",
                "content": "『옵세션』 — '서울' 근처(반경 10km) 영화관 5곳을 가까운 순으로 찾았어요. "
                "가장 가까운 곳은 롯데시네마 에비뉴엘(약 397m)이에요.",
            },
        ],
        "q": "9월 30일자로 찾아줘",
        "intent": "booking",
        "must": ["옵세션", "서울", "9월 30일"],
        "must_not": ["제목을 알려주시겠어요"],
        "note": "2026-09-28 실사용: 날짜 후속이 작품을 잃고 제목을 되묻던 문제. 작품·지역을 잇고 그 날짜 시간표",
    },
    {
        "name": "예매 대기 → 광역(서울 전체로)",
        "history": [
            {"role": "user", "content": "옵세션 예매하고싶어"},
            {"role": "assistant", "content": _REGION_ASK},
        ],
        "q": "서울 전체로 찾아줘",
        "intent": "booking",
        "must": ["옵세션", "'서울' 전역"],
        "must_not": ["근처(반경 10km)"],
        "note": "2026-09-28: 시·도 요청은 시청 좌표 반경 5곳이 아니라 서울 롯데관 전체에서 상영관 조회",
    },
    {
        "name": "예매 대기 → 구 단위(강남구)",
        "history": [
            {"role": "user", "content": "인턴 예매하고 싶어"},
            {"role": "assistant", "content": _INTERN_REGION_ASK},
        ],
        "q": "강남구에서 찾아줘",
        "intent": "booking",
        "must": ["인턴", "'강남구' 일대"],
        "note": "2026-09-28: 구 단위는 구 중심 반경 5km 롯데관, 남은 첫 회차 순",
    },
    {
        "name": "상영 안 하는 작품 → OTT 시청 링크",
        "history": [],
        "q": "인 타임은 어디서 볼 수 있어",
        "intent": "booking",
        "must": ["인 타임", "감상하실 수 있어요"],
        "watch_links_min": 2,
        "note": "2026-09-28: 상영작이 아니면 OTT 검색 링크 + TMDB 시청처를 watch_links로",
    },
    {
        "name": "시리즈 추천 뒤 '제일 최신 ○○가 뭐야' → 그 작품 소개",
        "history": [
            {"role": "user", "content": "스파이더맨 시리즈 추천해줘"},
            {
                "role": "assistant",
                "content": "[추천 카드] 1.『스파이더맨』(2002) 2.『스파이더맨: 브랜드 뉴 데이』(2026) "
                "3.『스파이더맨 2』(2004)\n스파이더맨 시리즈의 다양한 매력을 느낄 수 있는 작품들을 추천해 드립니다.",
            },
        ],
        "q": "제일 최신 스파이더맨이 뭐야",
        "intent": "evaluate",
        "rec_title_contains": "브랜드 뉴 데이",
        "must_not": ["카탈로그에 없어요"],
        "note": "2026-09-28 실사용 — recommend로 분류돼 기추천 dedup으로 0건 '카탈로그에 없어요'",
    },
    # 2026-10-01 — 봤어요·별점 기록 '후속'(09-30 실사용 버그가 전부 하네스 밖이었다). 하네스는
    # 비로그인이라 실제 기록은 pytest(test_chat_tracks·test_chat_agent 127건)가 지키고,
    # 여기서는 "실서버 판단 모델이 '봤어' 발화를 봤어요 도구로 보내고 정직하게 로그인 안내를
    # 하는가"(기록한 척·별점 창작 금지)만 응답 수준에서 본다. 비로그인이라 DB에 쓰지 않는다.
    {
        "name": "비로그인 '봤어 N점' → 로그인 안내(기록한 척 금지)",
        "history": [],
        "q": "인셉션 봤어 4점",
        "intent": "info",
        "must": ["로그인"],
        "must_not": ["표시했어요", "남겼어요", "표시했고"],
        "note": "봤어 발화가 봤어요 도구로 가야 info 로그인 안내가 나온다(general이면 안 나옴)",
    },
    {
        "name": "비로그인 '봤어'(별점 없음)도 봤어요 트랙 → 로그인 안내",
        "history": [],
        "q": "고지전 봤어",
        "intent": "info",
        "must": ["로그인"],
        "must_not": ["표시했어요", "남겼어요"],
        "note": "점수 없는 '봤어'도 봤어요 도구로 가야 한다. 말 안 한 별점을 안 남기는지는 비로그인으로는 "
        "볼 수 없고(응답이 고정 로그인 문구) pytest(test_rating_not_said_by_user_is_dropped)가 지킨다",
    },
    {
        "name": "비로그인 '최신 ○○ 봤어'도 봤어요 트랙 → 로그인 안내",
        "history": [],
        "q": "나 최신 스파이더맨 봤어",
        "intent": "info",
        "must": ["로그인"],
        "must_not": ["표시했어요", "남겼어요"],
        "note": "09-30 실사용: '최신 스파이더맨 봤어'가 평가/잡담으로 새 기록이 안 됐다",
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
    if scene.get("rec_year"):
        if not any(str(r.get("year")) == str(scene["rec_year"]) for r in recs):
            problems.append(f"카드 연도 {scene['rec_year']} 아님: {[r.get('year') for r in recs]}")
    if scene.get("watch_links_min"):
        links = (data.get("booking") or {}).get("watch_links") or []
        if len(links) < scene["watch_links_min"]:
            problems.append(f"watch_links {len(links)}개 < {scene['watch_links_min']}")
    if scene.get("rec_title_contains"):
        if not any(scene["rec_title_contains"] in (r.get("title") or "") for r in recs):
            problems.append(f"카드에 '{scene['rec_title_contains']}' 없음")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL)
    parser.add_argument("--only", default=None, help="장면 이름/질의 부분 문자열 필터")
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument(
        "--save", type=Path, default=None, help="장면별 답변·카드 JSON 저장(모델 비교용)"
    )
    args = parser.parse_args()

    scenes = [s for s in SCENES if not args.only or args.only in s["name"] or args.only in s["q"]]
    passed = 0
    failures: list[tuple[str, list[str], str]] = []
    rows: list[dict[str, Any]] = []
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
        rows.append(
            {
                "name": scene["name"],
                "q": scene["q"],
                "history": scene["history"],
                "reply": data.get("reply") or "",
                "titles": [
                    f"{x.get('title')}({x.get('year')})" for x in data.get("recommendations") or []
                ],
                "pass": not problems,
            }
        )
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
    if args.save:
        args.save.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"passed": passed, "total": len(scenes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
