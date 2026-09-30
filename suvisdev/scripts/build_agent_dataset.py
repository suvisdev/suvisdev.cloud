"""mova 채팅 '판단 단계' 학습 데이터셋 — 발화(+최근 대화+도구 결과) → 다음 행동 하나 (v9, 2026-09-29).

이해 v7(6칸 JSON)의 후속이다. 09-29 실사용 대화에서 6칸 양식에 자리가 없는 질문(출연진·현재 상영작·
직전 카드 전체 후속)이 전부 오답이 됐고, 도구 호출 에이전트 실측에서 "판단은 7.8B > Gemini, 답변 사실은
템플릿"이 확인됐다. 그래서 2.4B에게 **다음 행동 하나**(도구 호출 1개 또는 FINAL)만 가르친다.

라벨은 v7과 같이 **템플릿이 넣은 슬롯이 곧 정답**(교사 비용 0원). 어휘·조사·대화 템플릿은
`build_understanding_dataset.py`를 그대로 재사용한다. 입력 형식은 `agent_prompt.py`(서빙과 같은 파일).

출력(datasets/agent/, jsonl은 gitignore):
  agent_train.jsonl / agent_val.jsonl    템플릿 합성(패턴별 균형, 2단계 행 포함)
  agent_eval.jsonl                        멀티턴 17 + 단일 28 + 09-29 실대화 17 + 섀도 3 — 사람이 단 정답, 학습 금지
행 형식: {"system", "prompt", "completion", "pattern", "gold", "step"}

Usage (suvisdev 폴더, 표준 라이브러리만):
  python3 scripts/build_agent_dataset.py            # 기본 1,600행
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "apps"))  # agent_prompt.py가 허브 action_protocol을 import한다
import build_understanding_dataset as U  # noqa: E402, N812 — 어휘·조사·대화 템플릿 재사용

# 학습 분포 = 서빙 분포: 생성기와 서빙이 같은 agent_prompt.py를 읽는다(2026-09-30 v10 프롬프트 서빙 반영).
_PROMPT_FILE = (
    _ROOT / "apps/mova/adapter/outbound/llm" / os.getenv("AGENT_PROMPT_FILE", "agent_prompt.py")
)
_spec = importlib.util.spec_from_file_location("agent_prompt", _PROMPT_FILE)
AP = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(AP)

_OUT = _ROOT / "datasets/agent"
FINAL = "FINAL"
DIRECTORS = [
    "봉준호",
    "박찬욱",
    "홍상수",
    "이병헌",
    "연상호",
    "장항준",
    "토니 스콧",
    "크리스토퍼 놀란",
]


def call(name: str, **args: str | None) -> dict[str, Any]:
    return {"name": name, "arguments": {k: v for k, v in args.items() if v}}


# --- 채점(코랩·노트북 공용) ------------------------------------------------------------------


def norm(s: str | None) -> str:
    return re.sub(r"[\s『』'\"():.!?~,·]", "", s or "").lower()


def norm_region(s: str | None) -> str:
    return re.sub(r"(근처|쪽|에서|에|으로|로|일대|전체|전역)$", "", norm(s))


def match(pred: dict[str, Any] | str | None, gold: dict[str, Any] | str) -> bool:
    """도구 이름 + 정답에 있는 인자(title·region·date)가 표기 정규화 후 같아야 한다.
    query는 조건만 있으면 통과. 정답에 없는 title·region을 지어 넣으면 실패."""
    if gold == FINAL or pred == FINAL or pred is None:
        return pred == gold
    if not isinstance(pred, dict) or pred.get("name") != gold["name"]:
        return False
    ga, pa = gold["arguments"], pred.get("arguments") or {}
    for k, v in ga.items():
        p = pa.get(k, "")
        if k == "query":
            if not p:
                return False
        elif k == "region":
            if norm_region(p) != norm_region(v):
                return False
        elif norm(p) != norm(v) and not (k == "title" and norm(v) and norm(v) in norm(p)):
            return False
    return all(k in ga for k in ("title", "region") if k in pa)


# --- 가짜 도구 결과(2단계 행용) --------------------------------------------------------------


def res_recommend(rng: random.Random, titles: list[str]) -> dict[str, Any]:
    picks = rng.sample(titles, 3)
    return {
        "movies": [f"{t} ({rng.randint(1995, 2026)}) — {rng.choice(U.MOODS)} 작품" for t in picks]
    }


def res_details(rng: random.Random, t: str) -> dict[str, Any]:
    return {
        "title": f"{t} ({rng.randint(1995, 2026)})",
        "director": [rng.choice(DIRECTORS)],
        "cast": rng.sample(U.ACTORS, 4),
        "genres": rng.sample(U.GENRES, 2),
        "synopsis": f"{rng.choice(U.PLOTS)} 이야기.",
        "mova_reviews": {"count": rng.choice([0, 1, 3]), "avg_rating": rng.choice([None, 4.5])},
    }


def res_search(rng: random.Random, fam: str, members: list[str]) -> dict[str, Any]:
    years = sorted(U._years(rng, len(members)), reverse=True)
    newest = [f"{m} ({y})" for m, y in zip(members, years, strict=True)]
    return {"found": f"{fam} ({years[-1]})", "same_name_titles_newest_first": newest}


def res_showtimes(rng: random.Random, t: str, r: str | None) -> dict[str, Any]:
    if r:
        return {"status": "ok", "summary": U.booking_result(t, r)}
    return {"status": "need_region", "summary": U.region_ask(t)}


def res_where(rng: random.Random, t: str) -> dict[str, Any]:
    return {"title": t, "ott": rng.choice([["netflix"], ["wavve", "tving"], "정보 없음"])}


def res_now_showing(rng: random.Random, titles: list[str]) -> dict[str, Any]:
    return {"this_week_box_office": [f"{i}. {t}" for i, t in enumerate(rng.sample(titles, 8), 1)]}


# --- 1단계 패턴: (history, message, gold) ---------------------------------------------------

_REQ_TAIL = re.compile(
    r"\s*(영화\s*)?(추천해\s?줘|추천해\s?주세요|추천|찾아\s?줘|골라\s?줘|알려\s?줘|뭐\s*있어\??|있어\??|없어\??)\s*$"
)


def query_of(msg: str) -> str:
    return _REQ_TAIL.sub("", msg).strip() or msg


def p_rec_plain(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    _, msg, _, _ = U.p_recommend(rng, t)
    return [], msg, call("recommend_movies", query=query_of(msg))


def p_rec_actor(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    a = rng.choice(U.ACTORS)
    hist = []
    if rng.random() < 0.5:
        hist = [
            {"role": "user", "content": f"{t} 어때"},
            {"role": "assistant", "content": U.eval_reply(t)},
        ]
        msg = rng.choice([f"그럼 {a} 나오는 영화 다른 거 추천해줘", f"{a} 영화 다른 거 있어?"])
    else:
        msg = rng.choice([f"{a} 나오는 영화", f"{a} 주연 영화 추천", f"{a} 영화 뭐 있어?"])
    return hist, msg, call("recommend_movies", query=f"{a} 나오는 영화")


def p_rec_conditional(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    """조건이 붙은 추천은 '추천해줘'로 끝나도 recommend_movies다.

    v10이 '다른 영화'·'○○ 시리즈'·'입문용' 같은 조건부 추천을 recommend_for_me로 뺏겨(과트리거,
    09-29 재채점 실패 3건) v11에서 경계를 강화한다 — rec_for_me의 '맨 추천해줘'(조건 없음)와
    같은 '추천해줘' 표면인데 조건 유무로 갈리는 반례를 늘린다."""
    g, m = rng.choice(U.GENRES), rng.choice(U.MOODS)
    fr, th = rng.choice(U.FRANCHISES), rng.choice(U.THEMES)
    situ = rng.choice(["주말에", "퇴근하고", "비 오는 날", "혼자", "가족이랑", "밤에", "친구랑"])
    forms = [
        (f"{g} 영화 추천해줘", f"{g} 영화"),
        (f"{m} {g} 영화 추천해줘", f"{m} {g} 영화"),
        (f"{fr} 시리즈 추천해줘", f"{fr} 시리즈"),
        (f"{situ} 볼 영화 추천해줘", f"{situ} 볼 영화"),
        (f"{th} 영화 추천해줘", f"{th} 영화"),
        (f"{g} 입문용으로 추천해줘", f"{g} 입문용"),
        (f"{g} 처음 보는 사람용으로 추천해줘", f"{g} 처음 보는 사람"),
    ]
    hist: list[dict[str, str]] = []
    if rng.random() < 0.35:  # 한 편을 다룬 뒤 '다른 영화 추천해줘'도 조건부(recommend_movies)
        hist = [
            {"role": "user", "content": f"{t} 어때"},
            {"role": "assistant", "content": U.eval_reply(t)},
        ]
        forms += [("다른 영화 추천해줘", "다른 영화"), ("다른 거 추천해줘", "다른 영화")]
    msg, q = rng.choice(forms)
    return hist, msg + U.ending(rng, ("", "", "?", "!")), call("recommend_movies", query=q)


def p_eval_ask(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    _, msg, _, _ = U.p_evaluate(rng, t)
    return [], msg, call("get_movie_details", title=t)


def p_cast_ask(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    msg = rng.choice(
        [
            f"{t} 누가 나와?",
            f"{t}는 누가 나오지",
            f"{t} 출연진 알려줘",
            f"{t} 감독 누구야",
            f"{t} 주연이 누구야?",
            f"{josa(t, '은는')} 누가 만들었어",
        ]
    )
    return [], msg, call("get_movie_details", title=t)


def p_cast_context(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    if rng.random() < 0.5:
        hist = [
            {"role": "user", "content": f"{t} 어디서 볼 수 있어"},
            {
                "role": "assistant",
                "content": f"『{t}』은(는) 현재 상영작에서 확인되지 않아요. OTT 공개 정보도 아직 없어요.",
            },
        ]
    else:
        hist = [
            {"role": "user", "content": f"{rng.choice(U.GENRES)} 영화 하나만 추천해줘"},
            {"role": "assistant", "content": U.rec_reply([t], U._years(rng, 1))},
        ]
    msg = rng.choice(["누가나와", "누가 나오냐고", "출연진은?", "감독이 누구야", "그거 누가 나와?"])
    return hist, msg, call("get_movie_details", title=t)


def p_booking_full(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    r, d = rng.choice(U.REGIONS), rng.choice(U.TIMES)
    forms = [
        (f"{r}에서 {t} {d} 몇 시에 볼 수 있어?", call("showtimes", title=t, region=r, date=d)),
        (f"{t} {r} {d} 시간표 보여줘", call("showtimes", title=t, region=r, date=d)),
        (f"{r} {t} 예매하고 싶어", call("showtimes", title=t, region=r)),
        (f"{t} {r}에서 볼 수 있어?", call("showtimes", title=t, region=r)),
        (f"{d} {t} 상영해?", call("showtimes", title=t, date=d)),
    ]
    msg, g = rng.choice(forms)
    return [], msg, g


def p_booking_title_only(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    msg = rng.choice(
        [
            f"{t} 예매하고 싶어",
            f"{t} 시간표 보여줘",
            f"{t} 몇 시에 해?",
            f"{t} 극장에서 볼 수 있어?",
        ]
    )
    return [], msg, call("showtimes", title=t)


def p_booking_region_followup(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    r = rng.choice(U.REGIONS)
    hist = [
        {"role": "user", "content": f"{t} 예매하고 싶어"},
        {"role": "assistant", "content": U.region_ask(t)},
    ]
    msg = rng.choice([r, f"{r} 근처", f"{r}쪽", f"{r}에서 찾아줘", f"{r} 차로 갈게"])
    return hist, msg, call("showtimes", title=t, region=r)


def p_booking_date_followup(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    r, d = rng.choice(U.REGIONS), rng.choice(U.TIMES)
    hist = [
        {"role": "user", "content": f"{r}에서 {t} 예매하고 싶어"},
        {"role": "assistant", "content": U.booking_result(t, r)},
    ]
    msg = rng.choice([f"{d}자로 찾아줘", f"{d}는?", f"{d} 걸로 다시 봐줘", f"{d}에 볼래"])
    return hist, msg, call("showtimes", title=t, region=r, date=d)


def p_booking_region_change(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    hist, msg, g, _ = U.p_booking_region_change(rng, t)
    return hist, msg, call("showtimes", title=t, region=g["region"])


def p_theaters_near(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    r = rng.choice(U.REGIONS)
    msg = rng.choice(
        [
            f"{r} 근처 영화관 어디 있어?",
            f"{r}에 영화관 몇 개 있어?",
            f"{r} 근처에 어느 체인 지점이 있는지 알려줘",
        ]
    )
    return [], msg, call("showtimes", region=r)


def p_where_watch(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    if rng.random() < 0.3:
        hist = [
            {"role": "user", "content": f"{rng.choice(U.GENRES)} 영화 하나만 추천해줘"},
            {"role": "assistant", "content": U.rec_reply([t], U._years(rng, 1))},
        ]
        msg = rng.choice(["그거 어디서 볼 수 있어?", "그 영화 어디서 봐", "OTT에 있어?"])
    else:
        hist = []
        msg = rng.choice(
            [
                f"{t} 어디서 볼 수 있어",
                f"{josa(t, '은는')} 어디서 봐?",
                f"{t} 넷플릭스에 있어?",
                f"{t} 껀 어디서 볼수 있나",
            ]
        )
    return hist, msg, call("where_to_watch", title=t)


def p_now_showing(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    head = rng.choice(["", "", "음 ", "저기 ", "혹시 ", "그럼 ", "오늘 ", "이번 주 ", "주말에 "])
    body = rng.choice(
        [
            "요즘 극장에서 뭐 해",
            "최신 개봉영화 뭐 있는지 찾아봐",
            "지금 상영하는 영화 알려줘",
            "바로 예매할 수 있는 영화 찾아줘",
            "요즘 개봉한 영화 뭐 있어",
            "며칠 전에 개봉한 거 있는데",
            "최신영화 알려줘",
            "지금 박스오피스 1위가 뭐야",
            "극장에서 볼 만한 거 뭐 있어",
            "요즘 뭐가 인기야",
            "개봉작 목록 좀",
            "새로 나온 영화 뭐 있지",
            "요즘 영화관에서 뭐 하나",
            "당장 볼 수 있는 영화",
        ]
    )
    msg = (head + body + U.ending(rng, ("", "?", "??", "요", "!"))).strip()
    hist = []
    if rng.random() < 0.3:  # 직전 대화가 있어도 현재 상영작 질문은 now_showing
        hist = [
            {"role": "user", "content": f"{t} 어때"},
            {"role": "assistant", "content": U.eval_reply(t)},
        ]
    return hist, msg, call("now_showing")


def p_franchise_recent(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    fam = rng.choice(list(ctx["families"]))
    msg = rng.choice(
        [
            f"{fam} 요즘 개봉한 거 있지 않나",
            f"최신 {fam} 영화 말이야",
            f"{fam} 신작 나왔어?",
            f"{fam} 새로 나온 거 있어?",
            f"제일 최신 {josa(fam, '이가')} 뭐야",
        ]
    )
    return [], msg, call("search_movie", title=fam)


def p_latest_in_card(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    hist, msg, g, _ = U.p_latest_in_family(rng, ctx["families"])
    name = "showtimes" if g["intent"] == "booking" else "get_movie_details"
    return hist, msg, call(name, title=g["title"])


def p_context_that(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    hist, msg, g, _ = U.p_context_that(rng, t)
    if g["intent"] == "evaluate":
        return hist, msg, call("get_movie_details", title=t)
    return hist, msg, call("showtimes", title=t, region=g["region"], date=g["time"])


def p_choice(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    hist, msg, g, _ = U.p_choice_distinct(rng, ctx["families"])
    name = "showtimes" if g["intent"] == "booking" else "get_movie_details"
    return hist, msg, call(name, title=g["title"])


def p_card_all_followup(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    shown = rng.sample(ctx["titles"], 3)
    hist = [
        {
            "role": "user",
            "content": rng.choice(
                ["최신 개봉영화 뭐 있어", f"{rng.choice(U.GENRES)} 영화 추천해줘"]
            ),
        },
        {"role": "assistant", "content": U.rec_reply(shown, U._years(rng, 3))},
    ]
    msg = rng.choice(
        [
            "다 영화관에서 볼 수 있는 거야?",
            "이 중에 지금 상영 중인 거 있어?",
            "전부 극장에서 하는 거야?",
            "그걸 찾아보라고",
        ]
    )
    return hist, msg, call("now_showing")


def p_topic_switch(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    hist = [
        {"role": "user", "content": f"{t} 예매하고 싶어"},
        {"role": "assistant", "content": U.region_ask(t)},
    ]
    msg = rng.choice(
        [f"{t} 줄거리 알려줘", f"{t} 무슨 내용이야?", f"{t} 재밌어?", f"아 그 전에 {t} 누가 나와"]
    )
    return hist, msg, call("get_movie_details", title=t)


def p_general(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    _, msg, _, _ = U.p_general(rng, t)
    return [], msg, FINAL


def p_compound(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    msg = rng.choice(
        [
            f"{josa(t, '은는')} 몇 분짜리야? 몇 시에 해?",
            f"{t} 평점 괜찮아? 괜찮으면 예매할래",
            f"{t} 재밌어? 어디서 상영해?",
        ]
    )
    return [], msg, call("showtimes", title=t)


# --- v10 패턴(2026-09-29 저녁): 취향·유사·봤어요·취향 요약 + 09-29 운영 약점 ---------------------------
_RATINGS = ["3", "3.5", "4", "4.5", "5"]


def p_rec_for_me(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    g = rng.choice(U.GENRES)
    forms = [
        ("내 취향에 맞는 영화 추천해줘", "내 취향"),
        ("나한테 맞는 거 골라줘", "내 취향"),
        ("내가 본 영화 기준으로 추천해줘", "내 취향"),
        ("내 별점 취향대로 추천", "내 취향"),
        ("추천해줘", "내 취향"),
        ("영화 추천해줘", "내 취향"),
        ("뭐 볼까?", "내 취향"),
        ("오늘 뭐 보지", "내 취향"),
        ("볼 거 추천 좀", "내 취향"),
        (f"내 취향으로 {g} 영화 골라줘", g),
        (f"나한테 맞는 {g} 영화", g),
    ]
    msg, q = rng.choice(forms)
    hist = []
    if rng.random() < 0.3:
        hist = [
            {"role": "user", "content": f"{t} 어때"},
            {"role": "assistant", "content": U.eval_reply(t)},
        ]
    return hist, msg + U.ending(rng, ("", "", "?", "!")), call("recommend_for_me", query=q)


def p_similar_to(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    if rng.random() < 0.3:
        hist = [
            {"role": "user", "content": f"{rng.choice(U.GENRES)} 영화 하나만 추천해줘"},
            {"role": "assistant", "content": U.rec_reply([t], U._years(rng, 1))},
        ]
        msg = rng.choice(
            ["그거 같은 영화 더 없어?", "그 영화랑 비슷한 거 추천해줘", "이거 느낌의 작품 더"]
        )
    else:
        hist = []
        msg = rng.choice(
            [
                f"{t} 같은 영화 추천해줘",
                f"{t}{'이랑' if U._has_batchim(t) else '랑'} 비슷한 거 있어?",
                f"{t} 느낌의 작품 없을까",
                f"{t}처럼 재밌는 영화",
                f"{t}{'이랑' if U._has_batchim(t) else '랑'} 비슷한 영화 추천",
            ]
        )
    return hist, msg, call("similar_to", title=t)


def p_mark_watched(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    r = rng.choice(_RATINGS)
    if rng.random() < 0.5:
        hist = [
            {
                "role": "user",
                "content": rng.choice(
                    [f"{t} 어때", f"{rng.choice(U.GENRES)} 영화 하나만 추천해줘"]
                ),
            },
            {
                "role": "assistant",
                "content": rng.choice([U.eval_reply(t), U.rec_reply([t], U._years(rng, 1))]),
            },
        ]
        forms = [
            ("그거 봤어", None),
            (f"그거 봤어, {r}점", r),
            (f"봤어 {r}점", r),
            ("그 영화 봤어요 표시해줘", None),
            (f"이미 봤는데 {r}점 줄래", r),
        ]
    else:
        hist = []
        forms = [
            (f"{t} 봤어", None),
            (f"{t} 봤어요 표시해줘", None),
            (f"{t} 봤는데 {r}점", r),
            (f"{t} 별점 {r}", r),
            (f"{josa(t, '은는')} 봤어. {r}점 정도", r),
        ]
    msg, rating = rng.choice(forms)
    return hist, msg, call("mark_watched", title=t, rating=rating)


def p_taste_profile(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    head = rng.choice(["", "", "음 ", "근데 ", "그럼 ", "혹시 "])
    body = rng.choice(
        [
            "내 취향이 뭐야",
            "나 어떤 영화 좋아해",
            "내가 높게 준 영화 뭐야",
            "내 별점 기준으로 취향 알려줘",
            "나 취향 분석해줘",
            "내가 본 영화들 보면 무슨 장르 좋아하는 것 같아",
            "내 리뷰 보고 취향 정리해줘",
            "내가 좋아하는 장르가 뭐지",
            "나는 어떤 영화 취향이야",
            "내 취향 요약해줘",
            "내가 별점 제일 높게 준 게 뭐야",
        ]
    )
    return (
        [],
        (head + body + U.ending(rng, ("", "?", "??", "요", "!"))).strip(),
        call("taste_profile"),
    )


def p_referent_recent(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    """두 작품이 나왔으면 지시어는 뒤의 것(09-29 운영: 2턴 전 데자뷰를 이음)."""
    a, b = rng.sample(ctx["titles"], 2)
    r = rng.choice(U.REGIONS)
    hist = [
        {"role": "user", "content": f"{a} 어때"},
        {"role": "assistant", "content": U.eval_reply(a)},
        {"role": "user", "content": f"{b} 어때"},
        {"role": "assistant", "content": U.eval_reply(b)},
    ]
    msg, g = rng.choice(
        [
            ("예매 할 수 있는 곳 있나", call("showtimes", title=b)),
            (f"그거 {r}에서 볼 수 있어?", call("showtimes", title=b, region=r)),
            ("그거 어디서 봐?", call("where_to_watch", title=b)),
            ("누가 나와?", call("get_movie_details", title=b)),
            ("그거 봤어", call("mark_watched", title=b)),
        ]
    )
    return hist, msg, g


def p_cast_particle(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    """조사가 붙은 제목("데자뷰는 누가 나오지") — 발화 전체를 title에 넣지 않게."""
    msg = rng.choice(
        [
            f"{josa(t, '은는')} 누가 나오지",
            f"{josa(t, '은는')} 누가 나와?",
            f"{josa(t, '은는')} 어디서 볼 수 있지",
            f"{josa(t, '은는')} 어떤 영화야",
        ]
    )
    name = "where_to_watch" if "어디서" in msg else "get_movie_details"
    return [], msg, call(name, title=t)


# --- 2단계 패턴: 도구 결과가 있을 때 -----------------------------------------------------------


def p_final_after(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    """1단계 결과가 왔으니 FINAL — 같은 도구를 다시 부르지 않는 습관."""
    kind = rng.choice(["rec", "details", "where", "show", "now", "cast"])
    if kind == "rec":
        hist, msg, g = p_rec_plain(rng, t, ctx)
        res = res_recommend(rng, ctx["titles"])
    elif kind == "details":
        hist, msg, g = p_eval_ask(rng, t, ctx)
        res = res_details(rng, t)
    elif kind == "cast":
        hist, msg, g = p_cast_context(rng, t, ctx)
        res = res_details(rng, t)
    elif kind == "where":
        hist, msg, g = p_where_watch(rng, t, ctx)
        res = res_where(rng, t)
    elif kind == "show":
        hist, msg, g = p_booking_full(rng, t, ctx)
        res = res_showtimes(rng, t, g["arguments"].get("region"))
    else:
        hist, msg, g = p_card_all_followup(rng, t, ctx)
        res = res_now_showing(rng, ctx["titles"])
    return hist, msg, FINAL, [{"name": g["name"], "arguments": g["arguments"], "result": res}]


def p_franchise_two_step(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    fam = rng.choice(list(ctx["families"]))
    members = rng.sample(ctx["families"][fam], min(3, len(ctx["families"][fam])))
    res = res_search(rng, fam, members)
    newest = res["same_name_titles_newest_first"][0]
    if rng.random() < 0.5:
        msg = rng.choice([f"{fam} 요즘 개봉한 거 있지 않나", f"{fam} 신작 나왔어?"])
        gold: Any = FINAL  # 최신순 목록이 곧 답 — 템플릿이 쓴다
    else:
        msg = rng.choice(
            [
                f"제일 최신 {josa(fam, '이가')} 뭐야",
                f"가장 최근 {fam} 어때?",
                f"최신 {fam} 줄거리 알려줘",
            ]
        )
        gold = call("get_movie_details", title=newest)
    return [], msg, gold, [{"name": "search_movie", "arguments": {"title": fam}, "result": res}]


def p_need_region_then_final(rng: random.Random, t: str, ctx: dict[str, Any]) -> tuple:
    hist, msg, g = p_booking_title_only(rng, t, ctx)
    return (
        hist,
        msg,
        FINAL,
        [{"name": "showtimes", "arguments": g["arguments"], "result": res_showtimes(rng, t, None)}],
    )


PATTERNS: list[tuple[str, float]] = [
    ("rec_plain", 0.08),
    ("rec_actor", 0.03),
    ("rec_conditional", 0.06),  # v11: 조건부 추천이 recommend_for_me로 새는 것 방지
    ("eval_ask", 0.07),
    ("cast_ask", 0.05),
    ("cast_context", 0.04),
    ("booking_full", 0.07),
    ("booking_title_only", 0.05),
    ("booking_region_followup", 0.05),
    ("booking_date_followup", 0.03),
    ("booking_region_change", 0.03),
    ("theaters_near", 0.03),
    ("where_watch", 0.04),
    ("now_showing", 0.04),
    ("franchise_recent", 0.04),
    ("latest_in_card", 0.03),
    ("context_that", 0.05),
    ("choice", 0.03),
    ("card_all_followup", 0.03),
    ("topic_switch", 0.03),
    ("general", 0.03),
    ("compound", 0.02),
    ("final_after", 0.08),
    ("franchise_two_step", 0.03),
    ("need_region_then_final", 0.02),
    # v10
    ("rec_for_me", 0.05),
    ("similar_to", 0.05),
    ("mark_watched", 0.05),
    ("taste_profile", 0.02),
    ("referent_recent", 0.04),
    ("cast_particle", 0.03),
]
GENS = {name: globals()["p_" + name] for name, _ in PATTERNS}
josa = U.josa


def check(
    history: list[dict[str, str]], message: str, gold: Any, results: list[dict[str, Any]]
) -> str | None:
    """정답 인자는 발화·대화·도구 결과에 실제로 있어야 한다(근거 규칙)."""
    if gold == FINAL:
        return None
    context = norm(
        message + " ".join(m["content"] for m in history) + json.dumps(results, ensure_ascii=False)
    )
    for k, v in gold["arguments"].items():
        if k in ("title", "region", "date") and norm(v) not in context:
            return f"{k}이 근거에 없음"
    return None


def _row(history, message, gold, results, pattern) -> dict[str, Any]:
    return {
        "system": AP.SYSTEM_PROMPT,
        "prompt": AP.render_prompt(message, history, results or None),
        "completion": AP.format_action(gold),
        "pattern": pattern,
        "gold": gold,
        "step": 2 if results else 1,
    }


# --- 평가셋(사람이 단 정답, 학습 금지) ----------------------------------------------------------

_MULTITURN_GOLD: list[Any] = [
    call("showtimes", title="인턴"),
    call("showtimes", title="인턴", region="군자"),
    call("showtimes", title="인턴"),
    call("showtimes", title="인턴"),
    call("showtimes", region="군자역"),
    call("showtimes", title="인턴", region="군자", date="오늘"),
    call("showtimes", title="옵세션", region="군자역"),
    call("get_movie_details", title="옵세션"),
    call("now_showing"),
    call("showtimes", title="옵세션", region="군자"),
    call("get_movie_details", title="스파이더맨: 브랜드 뉴 데이"),
    call("showtimes", title="옵세션", region="강남"),
    call("showtimes", title="옵세션", region="서울", date="9월 30일"),
    call("showtimes", title="옵세션", region="서울 전체"),
    call("showtimes", title="인턴", region="강남구"),
    call("where_to_watch", title="인 타임"),
    call("get_movie_details", title="스파이더맨: 브랜드 뉴 데이"),
]

# 09-29 실사용 대화(cid 41) — 사용자가 "니 멋대로 대답한다"고 한 그 대화. (발화, 실제 도우미 답 요약, 정답 행동)
_CONV41: list[tuple[str, str, Any]] = [
    (
        "오늘 밤 가볍게 볼 한국 영화",
        "[추천 카드] 1.『가장 보통의 연애』(2019) 2.『밤의 해변에서 혼자』(2017) 3.『해운대』(2009)\n밤에 가볍게 즐기기 좋은 한국 영화 세 편을 추천해 드립니다.",
        call("recommend_movies", query="오늘 밤 가볍게 볼 한국 영화"),
    ),
    (
        "밤의 해변에서 혼자 껀 어디서 볼수 있나",
        "『밤의 해변에서 혼자』은(는) 최근 주간 박스오피스 기준으로 현재 상영작에서 확인되지 않아요. OTT 공개 정보도 아직 없어요.",
        call("where_to_watch", title="밤의 해변에서 혼자"),
    ),
    (
        "누가나와",
        "유부남과의 관계로 힘겨워하던 여배우 영희가 스스로를 되돌아보는 과정을 담은 영화입니다.",
        call("get_movie_details", title="밤의 해변에서 혼자"),
    ),
    (
        "누가 나오냐고",
        "유부남과의 관계로 힘겨워하던 여배우 영희가 낯선 도시와 강릉을 오가며 자신의 감정을 마주하는 이야기입니다.",
        call("get_movie_details", title="밤의 해변에서 혼자"),
    ),
    (
        "다른영화 추천해줘",
        "[추천 카드] 1.『데자뷰』(2006) 2.『인셉션』(2010) 3.『테넷』(2020)\n이전에 추천해 드린 작품 외에 다른 영화들을 골라 보았습니다.",
        call("recommend_movies", query="다른 영화"),
    ),
    (
        "데자뷰는 어디서 볼 수 있지",
        "『데자뷰』은(는) 현재 상영작에서 확인되지 않아요. 대신 디즈니+, 웨이브, 구글 플레이에서 감상하실 수 있어요.",
        call("where_to_watch", title="데자뷰"),
    ),
    (
        "데자뷰는 누가 나오지",
        "데자뷰 현상을 소재로 한 이 영화는 수사관이 과거를 엿볼 수 있는 기술로 테러를 막으려는 과정을 담았습니다.",
        call("get_movie_details", title="데자뷰"),
    ),
    (
        "왕과 사는남자인가?? 그거 재밌나",
        "계유정난으로 유배길에 오른 어린 왕 이홍위와 촌장 엄흥도의 기묘한 동거를 다룬 역사 드라마입니다. mova 리뷰 별점 5.0(리뷰 2건, 참고용).",
        call("get_movie_details", title="왕과 사는남자"),
    ),
    (
        "어때",
        "실화를 바탕으로 한 묵직한 서사가 인상적이라는 평이 있습니다.",
        call("get_movie_details", title="왕과 사는남자"),
    ),
    (
        "예매 할 수 있는곳이 있나",
        "『왕과 사는 남자』은(는) 현재 상영작에서 확인되지 않아요. OTT 공개 정보도 아직 없어요.",
        call("showtimes", title="왕과 사는남자"),
    ),
    (
        "그럼 유해진이 나오는 영화 다른거 추천해줘",
        "[추천 카드] 1.『럭키』(2016) 2.『공조』(2017) 3.『승리호』(2021)\n유해진 배우가 출연한 다른 작품들을 소개해 드릴게요.",
        call("recommend_movies", query="유해진 나오는 영화"),
    ),
    (
        "타짜 요즘 개봉한거 있지 않나",
        "[추천 카드] 1.『타짜』(2006)\n타짜 시리즈는 최근 개봉작이 없으나, 비슷한 범죄 분위기의 작품들을 안내해 드려요.",
        call("search_movie", title="타짜"),
    ),
    (
        "최신 타짜 영화 말이야",
        "중고 거래로 고장 난 세탁기를 구매한 수현이 사기꾼의 정체를 밝혀내려다 공포를 겪는 범죄 스릴러 영화입니다.",
        call("search_movie", title="타짜"),
    ),
    (
        "몇일 전에 개봉한거 있는데",
        "최근 개봉작이 많지 않아 한 편만 추천해 드립니다.",
        call("now_showing"),
    ),
    (
        "최신 개봉영화 뭐있는지 찾아봐",
        "[추천 카드] 1.『F1 더 무비』(2025) 2.『슈퍼맨』(2025) 3.『씨너스: 죄인들』(2025)\n최신 개봉작으로는 다양한 장르의 영화들이 준비되어 있습니다.",
        call("now_showing"),
    ),
    (
        "다 영화관에서 볼 수 있는거야?",
        "예매하실 작품을 카탈로그에서 찾지 못했어요. 정확한 제목으로 다시 알려주시겠어요?",
        call("now_showing"),
    ),
    (
        "그걸 찾아보라고 ;",
        "비슷한 제목이 여러 편이에요: 그것(2017) / 그물(2016) / 계절(2011).",
        call("now_showing"),
    ),
]


# 09-29 밤 실사용 대화(uid=1) — 예매를 원하는데 OTT(where_to_watch)로 답하고, '서울에서 제일 빠른걸로'를
# 작품 임의 지정+지역 되물음으로 처리해 사용자가 "아직도 말을 잘 못알아 듣는구나"라 한 대화. 응답은 실제(오답 포함),
# 정답 도구는 사용자 확인(2026-09-29): '제일 빠른걸로'=작품 무지정·서울 최속 회차, '예매라고'=시간표(OTT 아님).
_CONV_0929B: list[tuple[str, str, Any]] = [
    (
        "지금 당장 볼만한 영화가 뭐가 있을까",
        "지난주 박스오피스 기준 극장 상영작이에요: 1. 암살자(들) / 2. 타짜: 벨제붑의 노래 / 3. 오디세이 / 4. 인턴 …",
        call("now_showing"),
    ),
    (
        "2시간짜리 영화 추천해줘",
        "[추천 카드] 1.『13시간』 2.『다 큰 녀석들 2』 3.『127시간』\n러닝타임 조건에 맞춰 골라봤어요.",
        call("recommend_movies", query="2시간짜리 영화"),
    ),
    (
        "다 2시간짜리 영화야?",
        "세 작품 모두 2시간 내외예요 — 『13시간』 약 144분, 『다 큰 녀석들 2』 약 101분, 『127시간』 약 94분.",
        FINAL,
    ),
    (
        "9월 30일날 영화 예매할건데 무슨 영화가 있어",
        "현재 극장 상영작이에요: 『암살자(들)』 『타짜: 벨제붑의 노래』 『오디세이』 『인턴』 『옵세션』 …",
        call("now_showing"),
    ),
    (
        "서울에서 제일 빠른걸로 추천해줘",
        "『암살자(들)』 상영관을 찾아드릴게요. 어느 지역에서 보실 계획인가요?",  # 실제(오답): 작품 임의 지정+지역 되물음
        call("showtimes", region="서울"),  # 정답: 작품 무지정, 서울에서 제일 빠른 회차 탐색
    ),
    (
        "아직도 말을 잘 못알아 듣는구나",
        "죄송합니다. 지역과 이동 수단을 알려주시면 상영 시간표를 확인해 드릴게요.",
        FINAL,
    ),
    (
        "서울에서 볼거야",
        "'서울' 전역 롯데시네마에서 오늘 상영관을 찾아볼게요.",
        call("showtimes", region="서울"),
    ),
    (
        "암살자 말고 다른영화로 추천해줘",
        "[추천 카드] 1.『목요일 살인 클럽』\n암살자 말고 다른 작품을 골라봤어요.",
        call("recommend_movies", query="다른 영화"),
    ),
    (
        "아니 예매할거라고",
        "『목요일 살인 클럽』은 현재 상영작에서 확인되지 않아요. 대신 넷플릭스에서 볼 수 있어요.",  # 실제(오답): OTT
        call("showtimes", title="목요일 살인 클럽"),  # 정답: 예매(시간표) 의도
    ),
    (
        "저건 어디서 하는데",
        "『목요일 살인 클럽』은 현재 상영작에서 확인되지 않아요. 대신 넷플릭스에서 볼 수 있어요.",
        call("showtimes", title="목요일 살인 클럽"),
    ),
    (
        "예매라고................",
        "『목요일 살인 클럽』은 현재 상영작에서 확인되지 않아요. 대신 넷플릭스에서 볼 수 있어요.",
        call("showtimes", title="목요일 살인 클럽"),
    ),
]


_INCEPTION_CARD = "[추천 카드] 1.『인셉션』(2010)\n꿈속의 꿈을 파고드는 SF 스릴러예요."
_V10_EVAL: list[tuple[list[dict[str, str]], str, Any]] = [
    ([], "내 취향에 맞는 영화 추천해줘", call("recommend_for_me", query="내 취향")),
    ([], "추천해줘", call("recommend_for_me", query="내 취향")),
    ([], "기생충 같은 영화 추천해줘", call("similar_to", title="기생충")),
    ([], "인셉션이랑 비슷한 거 있어?", call("similar_to", title="인셉션")),
    (
        [
            {"role": "user", "content": "SF 영화 하나만 추천해줘"},
            {"role": "assistant", "content": _INCEPTION_CARD},
        ],
        "그거 봤어, 4점",
        call("mark_watched", title="인셉션", rating="4"),
    ),
    ([], "인터스텔라 봤어", call("mark_watched", title="인터스텔라")),
    ([], "내 취향이 뭐야", call("taste_profile")),
    ([], "데자뷰는 누가 나오지", call("get_movie_details", title="데자뷰")),
    (
        [],
        "비 오는 날 어울리는 영화",
        call("recommend_movies", query="비 오는 날 어울리는"),
    ),  # 조건 있으면 여전히 recommend_movies
]


def _eval_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    multi = U._ast_eval_module_lists("eval_chat_multiturn", "SCENES")
    if len(multi) != len(_MULTITURN_GOLD):
        raise SystemExit(f"멀티턴 장면 {len(multi)}개 ≠ 정답 {len(_MULTITURN_GOLD)}개")
    for scene, g in zip(multi, _MULTITURN_GOLD, strict=True):
        rows.append(_row(scene.get("history") or [], scene["q"], g, [], "harness:" + scene["name"]))
    for q in U._ast_eval_module_lists("eval_chat_queries", "SPECS"):
        text = q["q"]
        if text == "안녕":
            g: Any = FINAL
        elif "최신영화" in text:
            g = call("now_showing")
        else:
            g = call("recommend_movies", query=query_of(text))
        rows.append(_row([], text, g, [], "harness:single:" + text))
    hist: list[dict[str, str]] = []
    for i, (msg, reply, g) in enumerate(_CONV41):
        rows.append(_row(list(hist), msg, g, [], f"live:conv41:{i + 1}:{msg[:12]}"))
        hist += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
        hist = hist[-8:]
    hist = []
    for i, (msg, reply, g) in enumerate(_CONV_0929B):
        rows.append(_row(list(hist), msg, g, [], f"live:conv0929b:{i + 1}:{msg[:12]}"))
        hist += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
        hist = hist[-8:]
    for i, (h, msg, g) in enumerate(_V10_EVAL):
        rows.append(_row(h, msg, g, [], f"v10:{i + 1}:{msg[:12]}"))
    for trace, h, msg, g in U._SHADOW_EVAL:
        name = (
            "recommend_movies"
            if g["intent"] == "recommend"
            else ("showtimes" if g["intent"] == "booking" else "get_movie_details")
        )
        args = (
            {"query": query_of(msg)}
            if name == "recommend_movies"
            else {"title": g["title"], "region": g["region"]}
        )
        rows.append(_row(h, msg, call(name, **args), [], "shadow:" + trace))
    return rows


# --- 메인 ------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--n", type=int, default=1600)
    ap.add_argument("--seed", type=int, default=20260929)
    ap.add_argument("--out", type=Path, default=_OUT)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    titles = (
        [t.strip() for t in U._TITLES.read_text(encoding="utf-8").splitlines() if t.strip()]
        if U._TITLES.exists()
        else []
    )
    titles = [t for t in titles if "'" not in t and "『" not in t] or U.FALLBACK_TITLES
    families = {
        f: members
        for f in U.FRANCHISES
        if len(members := sorted({t for t in titles if t.startswith(f)})) >= 2
    } or U.FALLBACK_FAMILIES
    ctx = {"titles": titles, "families": families}
    titles_weighted = titles + U.FALLBACK_TITLES * 8

    eval_rows = _eval_rows()
    eval_keys = {r["prompt"] for r in eval_rows}
    total_w = sum(w for _, w in PATTERNS)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    rejected: Counter[str] = Counter()
    for pat, w in PATTERNS:
        quota, made = round(args.n * w / total_w), 0
        for _ in range(quota * 40):
            if made >= quota:
                break
            out = GENS[pat](rng, rng.choice(titles_weighted), ctx)
            hist, msg, gold = out[0], out[1], out[2]
            results = out[3] if len(out) > 3 else []
            row = _row(hist, msg, gold, results, pat)
            if row["prompt"] in seen or row["prompt"] in eval_keys:
                continue
            reason = check(hist, msg, gold, results)
            if reason:
                rejected[reason] += 1
                continue
            seen.add(row["prompt"])
            rows.append(row)
            made += 1
        if made < quota:
            print(f"⚠ {pat}: 할당 {quota} 중 {made}행만 생성")

    rng.shuffle(rows)
    n_val = max(1, len(rows) // 10)
    val, train = rows[:n_val], rows[n_val:]
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in (("train", train), ("val", val), ("eval", eval_rows)):
        with (args.out / f"agent_{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"train {len(train)} · val {len(val)} · eval {len(eval_rows)}  → {args.out}")
    print("패턴:", dict(sorted(Counter(r["pattern"] for r in rows).items(), key=lambda kv: -kv[1])))
    print(
        "행동:", dict(Counter(r["gold"] if r["gold"] == FINAL else r["gold"]["name"] for r in rows))
    )
    print(f"2단계 행: {sum(r['step'] == 2 for r in rows)}")
    if rejected:
        print("하드 체크 탈락:", dict(rejected))
    bad = [r["pattern"] for r in eval_rows if check([], r["prompt"], r["gold"], [])]
    if bad:
        print("⚠ 평가셋 정답이 근거 규칙과 어긋남:", bad)


if __name__ == "__main__":
    main()
