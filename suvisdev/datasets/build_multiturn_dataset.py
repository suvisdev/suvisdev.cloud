"""교사 데이터셋에 멀티턴(대화 이어가기) 예시를 만들어 붙인다 (2026-09-22).

기존 chat_teacher_dataset.jsonl 94건은 전부 단일턴인데, 서빙 프롬프트
(ChatPromptBuilder.build_prompt)는 최근 6턴 히스토리를 넣는다 — 학습에
후속 턴 예시가 0건이라 "다른건", "고마워" 같은 이어지는 발화에서 퇴행한다.

원본 1건을 씨앗으로 히스토리를 붙여 네 가지 후속 패턴을 만든다. 후속 발화
어휘는 프로덕션 chat_messages의 실사용 후속턴 42건에서 가져왔다.

- topic  : 다른 대화(j)를 히스토리로 얹고 본 턴은 원본 i 그대로 — 이전 맥락에
           오염되지 말 것. 정답은 i의 원본 completion(교사 호출 없음).
- again  : "다른건" 류. 서빙은 이미 추천한 작품을 카탈로그 단계에서 빼므로
           (market_chat_interactor의 dedup) 카탈로그에서도 뺀다. 뺄 게 없어
           원본이 유지되는 경우(코드의 폴백)는 히스토리에 나온 작품을 다시
           고르지 않고 정직하게 안내하는 걸 배운다.
- narrow : "2026년 작품으로" 류. 의도 섹션을 좁힌 조건으로 갱신하고 카탈로그는
           그대로 둬, 조건에 안 맞는 후보를 걸러내고 3편 미만이면 정직하게
           안내하는 걸 배운다.
- smalltalk : "고마워", "ㅎㅇ" 류. **카탈로그를 남겨둔 채** 추천하지 않는다 —
           기존 no-pick 10건은 전부 빈 카탈로그라 이 경우가 학습된 적이 없다
           (2026-09-17 A/B에서 인사에 3편 추천한 퇴행의 원인으로 보임).

again·narrow만 Gemini 교사를 부르고 나머지는 결정론이다. 생성된 정답은
카탈로그 그라운딩·편수·한자·hook 길이를 검증해 통과한 것만 쓴다.

프로젝트 모듈 의존 없이 google-genai·python-dotenv만 필요하다.

Usage (suvisdev/에서, .env의 GEMINI_API_KEY 사용):
  python datasets/build_multiturn_dataset.py --limit 6   # 소량 검증
  python datasets/build_multiturn_dataset.py
출력: datasets/chat_teacher_dataset_multiturn.jsonl, 재개용 캐시 .multiturn_cache.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]

SRC = _BACKEND / "datasets" / "chat_teacher_dataset.jsonl"
OUT = _BACKEND / "datasets" / "chat_teacher_dataset_multiturn.jsonl"
CACHE = _BACKEND / "datasets" / ".multiturn_cache.json"
SLEEP_SECONDS = 4.5  # Gemini 무료 티어 15req/min
MODEL = "gemini-3.1-flash-lite"

_USER_RE = re.compile(r"<<<USER_INPUT>>>(.*?)<<<END_USER_INPUT>>>", re.S)
_CATALOG_RE = re.compile(r"^- movie_id=(\d+) (.+?) \[.+?\]$", re.M)
_INTENT_RE = re.compile(r"^분류: (\S+) \| 정제: (.*?) \| 키워드: (.*)$", re.M)
_HANJA_RE = re.compile(r"[一-鿿]")
_YEAR_TAIL_RE = re.compile(r"\s*\(\d{4}\)\s*$")  # 교사가 붙인 연도 꼬리는 무시
# picks가 비었는데 "골라봤다"고 말하는 intro — 사용자에게 카드 0장이 가면서 말만 도는 모순
_CLAIM_RE = re.compile(r"엄선|골라|골랐|준비했|선정했|소개해 드립|추천해 드립니다|추천해 드릴게")

# 실사용 후속 발화(chat_messages 42건)에서 추린 어휘
_AGAIN = [
    "다른건",
    "이거 말곤 ??",
    "다른 영화 추천해줘 비슷한 느낌",
    "둘다 봤어",
    "그거 말고 다른거 없어?",
    "다 본거야 딴거",
    "비슷한 느낌으로 더 보여줘",
    "여러개 추천해줘",
]
# (발화, 의도 섹션에 덧붙일 조건)
_NARROW = [
    ("최근영화로 추천해줘", "최근 개봉작"),
    ("2026년 작품으로 알려줘", "2026년 개봉"),
    ("한국 영화로 추천해줘", "한국 영화"),
    ("짧게 끝나는 러닝타임 영화", "짧은 러닝타임"),
    ("좀 더 가벼운 걸로", "가벼운 분위기"),
    ("옛날 영화로 골라줘", "2000년 이전 개봉"),
]
# again은 "카탈로그에 없다"가 아니라 "이미 보여드렸다"가 사실이다 — 교사가 이걸
# 혼동해 거짓 안내를 쓰는 걸 막는다. 힌트는 교사 호출에만 붙이고 학습용 prompt에는
# 넣지 않는다(서빙 프롬프트와 어긋나면 안 된다).
_AGAIN_HINT = (
    "\n\n(작성 지침 — 답에 이 지침을 언급하지 마세요: 사용자는 위 [대화]에서 이미 "
    "추천받은 작품 말고 다른 작품을 원합니다. 카탈로그에 남아 있는 작품 중에서 "
    "평소대로 골라 추천하세요. 카탈로그가 비어 있을 때만 '더 보여드릴 새 작품이 "
    "없다'고 안내하고 조건을 바꿔볼지 되물으세요 — 이때도 '카탈로그에 없다'고는 "
    "하지 마세요.)"
)

_SMALLTALK = [
    ("고마워", "천만에요! 또 찾는 영화가 생기면 말씀해 주세요."),
    ("고마워요 잘 볼게요", "재미있게 보세요! 다 보고 나서 다른 작품이 필요하면 불러 주세요."),
    ("ㅎㅇ", "안녕하세요! 어떤 영화를 찾으시나요?"),
    ("ㅇㅋ", "네! 더 필요한 게 있으면 말씀해 주세요."),
    ("ㅋㅋㅋ", "어떤 영화를 찾으시는지 알려주시면 골라드릴게요."),
    ("잘 볼게", "좋은 시간 되세요! 다음에 또 찾아주세요."),
    ("수고", "감사합니다! 또 추천이 필요하면 말씀해 주세요."),
    ("안녕", "안녕하세요! 어떤 분위기의 영화를 찾고 계신가요?"),
]


def _user_query(prompt: str) -> str:
    return _USER_RE.findall(prompt)[-1]


def _catalog(prompt: str) -> list[tuple[int, str]]:
    return [(int(mid), title) for mid, title in _CATALOG_RE.findall(prompt)]


def _set_turn(prompt: str, history: list[tuple[str, str]], query: str) -> str:
    """[대화] 섹션을 히스토리 + 이번 발화로 다시 쓴다(서빙 렌더링과 동일 형식)."""
    head = prompt.rsplit("[대화]", 1)[0]
    lines = ["[대화]"]
    for role, content in history:
        lines.append(f"{'사용자' if role == 'user' else 'Mova'}: {content}")
    lines.append(f"사용자: <<<USER_INPUT>>>{query}<<<END_USER_INPUT>>>")
    lines.append("JSON:")
    return head + "\n".join(lines)


def _drop_from_catalog(prompt: str, movie_ids: set[int]) -> str:
    keep = [
        line
        for line in prompt.split("\n")
        if not (
            line.startswith("- movie_id=") and int(line.split("=", 1)[1].split(" ", 1)[0]) in movie_ids
        )
    ]
    return "\n".join(keep)


def _narrow_intent(prompt: str, condition: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f"분류: filter_and | 정제: {m.group(2)} ({condition}) | 키워드: {m.group(3)}, {condition}"

    return _INTENT_RE.sub(repl, prompt, count=1)


def _validate(
    raw: str, prompt: str, *, forbid_ids: set[int], need_pick: bool = False
) -> tuple[dict | None, str]:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        return None, "JSON 없음"
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 실패: {e}"
    intro, picks = data.get("intro"), data.get("picks")
    if not isinstance(intro, str) or not isinstance(picks, list):
        return None, "intro/picks 형식 오류"
    if len(picks) > 3:
        return None, f"picks {len(picks)}편(최대 3)"
    catalog = dict(_catalog(prompt))
    if need_pick and not picks and catalog:
        # 조건은 그대로인데 후보가 남아 있다 — "보여드릴 게 없다"는 거짓이 된다
        return None, f"카탈로그 {len(catalog)}편 남았는데 0편 추천"
    if not picks and _CLAIM_RE.search(intro):
        return None, f"0편인데 추천했다는 intro: {intro[:40]}"
    for p in picks:
        mid = p.get("movie_id")
        if mid not in catalog:
            return None, f"카탈로그 밖 movie_id={mid}"
        if mid in forbid_ids:
            return None, f"이미 추천한 movie_id={mid} 재등장"
        # 카탈로그 원문에 공백이 겹쳐 들어간 제목이 있다 — 앱은 제목을 DB 값으로
        # 덮어쓰므로 공백 차이는 무해하다. 연도 꼬리와 같이 무시한다.
        def norm(t: str) -> str:
            return re.sub(r"\s+", " ", _YEAR_TAIL_RE.sub("", t)).strip()

        if norm(str(p.get("title", ""))) != norm(catalog[mid]):
            return None, f"title 불일치: {p.get('title')} != {catalog[mid]}"
        if len(str(p.get("hook", ""))) > 40:
            return None, "hook 40자 초과"
    if _HANJA_RE.search(json.dumps(data, ensure_ascii=False)):
        return None, "한자 포함"
    return data, ""


def _ask_teacher(prompt: str, client) -> str:
    return client.models.generate_content(model=MODEL, contents=prompt).text


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="교사 호출 건수 상한(0=제한 없음)")
    return parser.parse_args(argv)


def main() -> None:
    from dotenv import load_dotenv
    from google import genai

    args = _parse_args()
    load_dotenv(_BACKEND / ".env")
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    rows = [json.loads(line) for line in SRC.open(encoding="utf-8") if line.strip()]
    seeds = [  # picks가 있는 원본만 씨앗 — 히스토리에 얹을 Mova 답변이 필요하다
        (i, r) for i, r in enumerate(rows) if json.loads(r["completion"]).get("picks")
    ]
    cache: dict[str, str] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rng = random.Random(20260922)
    out: list[dict] = []
    calls = skipped = 0

    def teacher_row(
        prompt: str, *, src: int, aug: str, forbid: set[int], hint: str = "", need_pick: bool = False
    ) -> None:
        nonlocal calls, skipped
        if args.limit and calls >= args.limit:
            return
        key = f"{aug}:{src}"
        if key not in cache:
            try:
                cache[key] = _ask_teacher(prompt + hint, client)
            except Exception as e:  # noqa: BLE001 — 한 건 실패해도 나머지는 진행
                print(f"[{key}] 교사 호출 실패: {e}", flush=True)
                skipped += 1
                return
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            calls += 1
            time.sleep(SLEEP_SECONDS)
        data, reason = _validate(cache[key], prompt, forbid_ids=forbid, need_pick=need_pick)
        if data is None:
            print(f"[{key}] 버림 — {reason}", flush=True)
            cache.pop(key, None)  # 다음 실행에서 다시 시도
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            skipped += 1
            return
        out.append(
            {
                "prompt": prompt,
                "completion": json.dumps(data, ensure_ascii=False),
                "src": src,
                "aug": aug,
            }
        )
        print(f"[{key}] {len(data['picks'])}편 · {data['intro'][:40]}", flush=True)

    for i, row in seeds:
        prompt, completion = row["prompt"], json.loads(row["completion"])
        query = _user_query(prompt)
        intro = completion["intro"]
        shown = {p["movie_id"] for p in completion["picks"]}
        history = [("user", query), ("assistant", intro)]

        # topic — 다른 대화를 히스토리로 얹어도 이번 턴 조건만 따른다(교사 호출 없음)
        j, prev = rng.choice([s for s in seeds if s[0] != i])
        prev_completion = json.loads(prev["completion"])
        out.append(
            {
                "prompt": _set_turn(
                    prompt,
                    [("user", _user_query(prev["prompt"])), ("assistant", prev_completion["intro"])],
                    query,
                ),
                "completion": row["completion"],
                "src": i,
                "aug": f"mt_topic_{j}",
            }
        )

        # smalltalk — 카탈로그가 있는 상태에서 추천하지 않기(교사 호출 없음)
        if rng.random() < 0.35:
            talk, reply = rng.choice(_SMALLTALK)
            out.append(
                {
                    "prompt": _set_turn(prompt, history, talk),
                    "completion": json.dumps({"intro": reply, "picks": []}, ensure_ascii=False),
                    "src": i,
                    "aug": "mt_smalltalk",
                }
            )

        # again — 서빙 dedup과 같이 이미 보여준 작품을 카탈로그에서 뺀다
        again_prompt = _set_turn(_drop_from_catalog(prompt, shown), history, rng.choice(_AGAIN))
        teacher_row(
            again_prompt, src=i, aug="mt_again", forbid=shown, hint=_AGAIN_HINT, need_pick=True
        )

        # narrow — 의도만 좁히고 카탈로그는 그대로(걸러내기·정직한 편수 부족 안내)
        if rng.random() < 0.55:
            utter, condition = rng.choice(_NARROW)
            narrow_prompt = _set_turn(_narrow_intent(prompt, condition), history, utter)
            teacher_row(narrow_prompt, src=i, aug="mt_narrow", forbid=set())

    with OUT.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[multiturn] 씨앗 {len(seeds)}건 → {len(out)}건 (교사 호출 {calls} · 버림 {skipped}): {OUT}")


if __name__ == "__main__":
    main()
