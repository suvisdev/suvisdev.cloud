"""v3 추가 학습 데이터 — 정직한 부족 안내 · 배우 질의 · 재요청 보강 (2026-09-22).

v2(09-22) 평가에서 5점 미만 14건의 사유가 한곳으로 수렴했다: "카탈로그에 없는
작품을 억지로 끼워 맞춘다". 원인은 데이터 분포다 — picks가 0~2편인 행은 149행
있지만 **intro에 "부족·못 찾음" 표현이 있는 행은 28행(5%)뿐**이라, 모델이
"편수는 조절하되 말투는 항상 확신"을 배웠다.

생성 항목(v3 README ①~④):
  honest   조건과 어긋나는 카탈로그 → picks 0 + 정직한 intro   (교사 호출 없음)
  again_empty  재요청인데 카탈로그가 빔 → picks 0 + "더 없다"  (교사 호출 없음)
  actor    배우 질의 + 그 배우 작품 카탈로그 → 3편 선택         (교사)
  seen     이미 본 작품을 빼고 나머지에서 고르기                 (교사)

정직 안내를 템플릿으로 두는 이유: v2에서 교사가 "0편인데 골라봤습니다"류 모순
intro를 반복해 13건을 버렸다. 정답이 자명한 케이스는 사람이 문구를 고정하는 편이
데이터 품질이 높다.

Usage (suvisdev/에서):
  python datasets/build_v3_additions.py --actors <배우JSON> [--limit N]
출력: datasets/chat_teacher_dataset_v3_add.jsonl
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
OUT = _BACKEND / "datasets" / "chat_teacher_dataset_v3_add.jsonl"
CACHE = _BACKEND / "datasets" / ".v3_cache.json"
SLEEP_SECONDS = 4.5
MODEL = "gemini-3.1-flash-lite"

_USER_RE = re.compile(r"<<<USER_INPUT>>>(.*?)<<<END_USER_INPUT>>>", re.S)
_CAT_LINE_RE = re.compile(r"^- movie_id=\d+ .*$", re.M)
_CAT_RE = re.compile(r"^- movie_id=(\d+) (.+?) \[.+?\]$", re.M)
_INTENT_RE = re.compile(r"^분류: (\S+) \| 정제: (.*?) \| 키워드: (.*)$", re.M)
_HANJA_RE = re.compile(r"[一-鿿]")
_YEAR_TAIL_RE = re.compile(r"\s*\(\d{4}\)\s*$")

# 조건에 맞는 작품이 없을 때 쓰는 문구. "찾지 못했다"를 분명히 말하는 것이 핵심.
_HONEST = [
    "{q}에 해당하는 작품을 카탈로그에서 찾지 못했어요. 다른 조건으로 알려주시겠어요?",
    "지금 목록에는 {q} 조건에 맞는 작품이 없네요. 장르나 분위기를 바꿔 말씀해 주세요.",
    "{q} 조건에 맞는 작품을 못 찾았습니다. 비슷한 다른 키워드로 찾아볼까요?",
    "아쉽게도 {q}에 맞는 작품이 카탈로그에 없어요. 다른 취향을 알려주시면 다시 골라볼게요.",
    "{q}으로는 맞는 작품이 잡히지 않네요. 조건을 조금 넓혀 주시면 찾아보겠습니다.",
    "찾아봤지만 {q} 조건을 만족하는 작품이 없습니다. 다른 방식으로 물어봐 주세요.",
]
_AGAIN_EMPTY = [
    "이미 보여드린 작품 외에 더 소개할 작품이 없어요. 다른 장르나 분위기로 찾아볼까요?",
    "아쉽게도 새로 보여드릴 작품이 남아 있지 않네요. 조건을 바꿔 말씀해 주세요.",
    "더 추천할 작품이 없습니다. 다른 취향을 알려주시면 그에 맞춰 찾아볼게요.",
    "남은 작품이 없어요. 장르를 바꾸거나 연도를 넓혀서 다시 물어봐 주시겠어요?",
]
_AGAIN_UTTER = ["다른건", "이거 말곤 ??", "그거 말고 다른거 없어?", "다 본거야 딴거", "더 없어?"]
_SEEN_UTTER = ["둘다 봤어", "그거 다 봤어", "셋 다 본 거야", "이미 본 작품들이야"]
_ACTOR_UTTER = ["{a} 나오는 영화", "{a} 영화 추천해줘", "{a} 출연작 추천", "{a} 나온 작품 뭐 있어"]
_GENRE_UTTER = ["{g} 영화 추천해줘", "{g} 장르로 골라줘", "{g} 영화 뭐 볼까", "{g} 쪽으로 추천해줘"]


def _user_query(prompt: str) -> str:
    return _USER_RE.findall(prompt)[-1]


def _catalog(prompt: str) -> list[tuple[int, str]]:
    return [(int(m), t) for m, t in _CAT_RE.findall(prompt)]


def _replace_catalog(prompt: str, lines: list[str]) -> str:
    """카탈로그 줄 전체를 새 목록으로 바꾼다. 빈 목록이면 줄을 지운다."""
    out, done = [], False
    for line in prompt.split("\n"):
        if _CAT_LINE_RE.fullmatch(line):
            if not done:
                out.extend(lines)
                done = True
            continue
        out.append(line)
    return "\n".join(out)


def _set_turn(prompt: str, history: list[tuple[str, str]], query: str) -> str:
    head = prompt.rsplit("[대화]", 1)[0]
    lines = ["[대화]"]
    for role, content in history:
        lines.append(f"{'사용자' if role == 'user' else 'Mova'}: {content}")
    lines.append(f"사용자: <<<USER_INPUT>>>{query}<<<END_USER_INPUT>>>")
    lines.append("JSON:")
    return head + "\n".join(lines)


def _set_intent(prompt: str, refined: str, keywords: list[str], kind: str = "mood") -> str:
    def repl(_m: re.Match[str]) -> str:
        return f"분류: {kind} | 정제: {refined} | 키워드: {', '.join(keywords)}"

    return _INTENT_RE.sub(repl, prompt, count=1)


def _validate(raw: str, prompt: str) -> tuple[dict | None, str]:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0:
        return None, "JSON 없음"
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        return None, f"파싱 실패: {e}"
    picks = data.get("picks")
    intro = data.get("intro")
    if not isinstance(picks, list) or not isinstance(intro, str) or not intro.strip():
        return None, "형식 오류"
    if len(picks) > 3:
        return None, f"picks {len(picks)}편"
    cat = dict(_catalog(prompt))
    for p in picks:
        mid = p.get("movie_id")
        if mid not in cat:
            return None, f"카탈로그 밖 {mid}"
        norm = lambda t: re.sub(r"\s+", " ", _YEAR_TAIL_RE.sub("", str(t))).strip()  # noqa: E731
        if norm(p.get("title", "")) != norm(cat[mid]):
            return None, "title 불일치"
        if len(str(p.get("hook", ""))) > 40:
            return None, "hook 40자 초과"
    if _HANJA_RE.search(raw):
        return None, "한자"
    return data, ""


def main() -> None:
    from dotenv import load_dotenv
    from google import genai

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--actors", required=True, help="배우별 출연작 JSON")
    ap.add_argument("--genres", help="장르 태그가 붙은 영화 JSON(장르 불일치 예시용)")
    ap.add_argument("--limit", type=int, default=0, help="교사 호출 상한(0=무제한)")
    args = ap.parse_args()

    load_dotenv(_BACKEND / ".env")
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cache: dict[str, str] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rng = random.Random(20260922)

    rows = [json.loads(line) for line in SRC.open(encoding="utf-8") if line.strip()]
    seeds = [(i, r) for i, r in enumerate(rows) if json.loads(r["completion"]).get("picks")]
    actors = json.loads(Path(args.actors).read_text(encoding="utf-8"))
    base = seeds[0][1]["prompt"]  # 프롬프트 골격(카탈로그·의도·대화만 갈아끼운다)
    out: list[dict] = []
    calls = skipped = 0

    def teacher(prompt: str, key: str, aug: str, src: int) -> None:
        nonlocal calls, skipped
        if args.limit and calls >= args.limit:
            return
        if key not in cache:
            try:
                cache[key] = client.models.generate_content(model=MODEL, contents=prompt).text
            except Exception as e:  # noqa: BLE001
                print(f"[{key}] 교사 실패: {e}", flush=True)
                skipped += 1
                return
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            calls += 1
            time.sleep(SLEEP_SECONDS)
        data, why = _validate(cache[key], prompt)
        if data is None:
            print(f"[{key}] 버림 — {why}", flush=True)
            cache.pop(key, None)
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
        print(f"[{key}] {len(data['picks'])}편 · {data['intro'][:45]}", flush=True)

    # ① honest — 배우 질의 + **다른 배우**의 작품 카탈로그 → 0편 + 정직 안내.
    #    원본끼리 카탈로그를 무작위 교차하면 우연히 조건에 맞는 작품이 섞여
    #    "맞는 게 있는데 없다고 답하라"는 틀린 라벨이 된다. 배우는 겹칠 수 없으므로
    #    불일치가 보장된다(2026-09-22 설계 수정).
    for idx, a in enumerate(actors):
        other = actors[(idx + 7) % len(actors)]
        if other["name"] == a["name"] or len(other["movies"]) < 4:
            continue
        q = rng.choice(_ACTOR_UTTER).format(a=a["name"])
        lines = [
            f"- movie_id={m[0]} {m[1]} ({m[2] or '연도 미상'}) [배우]" for m in other["movies"]
        ]
        prompt = _set_turn(
            _set_intent(_replace_catalog(base, lines), q, [a["name"], "영화", q]), [], q
        )
        intro = rng.choice(_HONEST).format(q=f"「{a['name']}」 출연작")
        out.append(
            {
                "prompt": prompt,
                "completion": json.dumps({"intro": intro, "picks": []}, ensure_ascii=False),
                "src": 800 + idx,
                "aug": "v3_honest",
            }
        )

    # ①-2 honest(장르) — 질의 장르를 **갖지 않는** 영화만 카탈로그에 넣는다.
    #     배우 불일치 한 종류만으로는 "없다고 말하기"의 표현이 단조로워진다.
    #     장르 태그로 필터하므로 우연히 조건에 맞는 작품이 섞일 수 없다.
    if args.genres:
        movies = json.loads(Path(args.genres).read_text(encoding="utf-8"))
        all_genres = sorted({g for m in movies for g in m["genres"]})
        for gi, want in enumerate(all_genres):
            pool = [m for m in movies if want not in m["genres"]]
            if len(pool) < 12:
                continue
            for k in range(4):  # 장르마다 4건 — 카탈로그 구성을 달리해 표현을 넓힌다
                picked = rng.sample(pool, 12)
                lines = [
                    f"- movie_id={m['id']} {m['title']} ({m['year'] or '연도 미상'}) [태그]"
                    for m in picked
                ]
                q = rng.choice(_GENRE_UTTER).format(g=want)
                prompt = _set_turn(
                    _set_intent(_replace_catalog(base, lines), q, [want, "영화", q]), [], q
                )
                out.append(
                    {
                        "prompt": prompt,
                        "completion": json.dumps(
                            {"intro": rng.choice(_HONEST).format(q=f"「{want}」"), "picks": []},
                            ensure_ascii=False,
                        ),
                        "src": 700 + gi * 10 + k,
                        "aug": "v3_honest_genre",
                    }
                )

    # ② again_empty — 재요청인데 카탈로그가 비었다
    for i, row in seeds:
        if rng.random() > 0.4:
            continue
        c = json.loads(row["completion"])
        q = _user_query(row["prompt"])
        prompt = _set_turn(
            _replace_catalog(row["prompt"], []),
            [("user", q), ("assistant", c["intro"])],
            rng.choice(_AGAIN_UTTER),
        )
        out.append(
            {
                "prompt": prompt,
                "completion": json.dumps(
                    {"intro": rng.choice(_AGAIN_EMPTY), "picks": []}, ensure_ascii=False
                ),
                "src": i,
                "aug": "v3_again_empty",
            }
        )

    # ③ actor — 배우 질의 + 그 배우 작품으로 채운 카탈로그
    for idx, a in enumerate(actors):
        name, movies = a["name"], a["movies"]
        if len(movies) < 4:
            continue
        lines = [f"- movie_id={m[0]} {m[1]} ({m[2] or '연도 미상'}) [배우]" for m in movies]
        q = rng.choice(_ACTOR_UTTER).format(a=name)
        prompt = _set_turn(
            _set_intent(_replace_catalog(base, lines), q, [name, "영화", q]), [], q
        )
        teacher(prompt, f"actor:{idx}", "v3_actor", 900 + idx)

    # ④ seen — 이미 본 작품을 빼고 나머지에서 고르기
    for i, row in seeds:
        if rng.random() > 0.25:
            continue
        c = json.loads(row["completion"])
        shown = {p["movie_id"] for p in c["picks"]}
        remain = [
            ln
            for ln in _CAT_LINE_RE.findall(row["prompt"])
            if int(ln.split("=", 1)[1].split(" ", 1)[0]) not in shown
        ]
        if len(remain) < 3:
            continue
        titles = ", ".join(p["title"] for p in c["picks"])
        prompt = _set_turn(
            _replace_catalog(row["prompt"], remain),
            [("user", _user_query(row["prompt"])), ("assistant", f"{c['intro']} ({titles})")],
            rng.choice(_SEEN_UTTER),
        )
        teacher(prompt, f"seen:{i}", "v3_seen", i)

    with OUT.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds: dict[str, int] = {}
    for r in out:
        kinds[r["aug"]] = kinds.get(r["aug"], 0) + 1
    print(f"\n[v3] {len(out)}행 생성 {kinds} (교사 {calls} · 버림 {skipped}) → {OUT}")


if __name__ == "__main__":
    main()
