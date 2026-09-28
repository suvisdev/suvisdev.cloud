"""mova 오케스트레이터 '이해 단계' 학습 데이터셋 — 발화(+최근 대화) → 슬롯 JSON.

목적: 지금 이해 단계는 EXAONE 7.8B에 예시 몇 개를 보여주는 프롬프트 방식이다(VRAM 4.9GB·발화당
1~2초). 출력 형식이 좁은 JSON 한 개라, 2.4B를 이 형식에 맞춰 학습하면 7.8B를 대체할 수 있다.

라벨을 교사 모델에게 받지 않는다 — **템플릿이 넣은 슬롯이 곧 정답**이다(작품·지역·시각·체인을
템플릿에 끼워 발화를 만들므로 무엇이 들어갔는지 안다). 교사 비용 0원이고, 교사의 실수를 학생이
배우지 않는다. 실사용 트래픽이 거의 없어(09-28 실측: 7일간 전부 하네스) 실제 로그는 원천이 못 된다.

입력 형식은 운영 어댑터(`exaone_chat_understanding_adapter.py`)와 **바이트 단위로 같게** 만든다:
SYSTEM_PROMPT를 그 파일에서 ast로 읽어 오고, 최근 대화 렌더(최근 4턴·턴당 160자)도 같은 규칙.

출력(datasets/understanding/, jsonl은 gitignore):
  understanding_train.jsonl  템플릿 합성(패턴별 균형)
  understanding_val.jsonl    같은 분포 10% — 에폭 선택용
  understanding_eval.jsonl   **하네스 장면 36개에 사람이 단 정답** — 학습에 절대 안 섞는 실사용 기반 평가셋
행 형식: {"system", "prompt", "completion", "pattern", "gold"}  (v5 노트북의 prompt/completion과 호환)

Usage (suvisdev 폴더, 표준 라이브러리만):
  python3 scripts/build_understanding_dataset.py            # 기본 1,600행
  python3 scripts/build_understanding_dataset.py --n 3000 --seed 7
"""

from __future__ import annotations

import argparse
import ast
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_ADAPTER = _ROOT / "apps/mova/adapter/outbound/llm/exaone_chat_understanding_adapter.py"
_OUT = _ROOT / "datasets/understanding"
_TITLES = _OUT / "titles.txt"


# --- 운영 어댑터와 같은 입력 형식 ------------------------------------------------------------


def _adapter_constants() -> dict[str, Any]:
    """SYSTEM_PROMPT·_HISTORY_TURNS·_HISTORY_CHARS를 import 없이 ast로 읽는다(의존성 0)."""
    tree = ast.parse(_ADAPTER.read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"SYSTEM_PROMPT", "_HISTORY_TURNS", "_HISTORY_CHARS"}:
                out[name] = ast.literal_eval(node.value)
    return out


_C = _adapter_constants()
SYSTEM_PROMPT: str = _C["SYSTEM_PROMPT"]


def render_prompt(message: str, history: list[dict[str, str]]) -> str:
    lines = []
    for m in history[-_C["_HISTORY_TURNS"] :]:
        content = (m.get("content") or "").strip()
        if content:
            who = "사용자" if m.get("role") == "user" else "도우미"
            lines.append(f"{who}: {content[: _C['_HISTORY_CHARS']]}")
    rendered = "\n".join(lines)
    return (f"[최근 대화]\n{rendered}\n\n" if rendered else "") + f"[발화]\n{message}"


def gold(
    intent: str,
    title: str | None = None,
    region: str | None = None,
    time: str | None = None,
    chain: str | None = None,
    followup: bool = False,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "title": title,
        "region": region,
        "time": time,
        "chain": chain,
        "followup": followup,
    }


def completion(g: dict[str, Any]) -> str:
    # 운영 프롬프트 예시와 같은 키 순서·구분자(공백 없음)
    return json.dumps(g, ensure_ascii=False, separators=(",", ":"))


# --- 어휘 ------------------------------------------------------------------------------------

REGIONS = [
    "군자",
    "강남",
    "강남역",
    "홍대입구역",
    "홍대",
    "잠실",
    "건대입구",
    "신촌",
    "여의도",
    "왕십리",
    "용산",
    "영등포",
    "노원",
    "수원",
    "판교",
    "일산",
    "분당",
    "인천 부평",
    "부산 서면",
    "해운대",
    "대전 둔산동",
    "광주 상무",
    "대구 동성로",
    "강남구",
    "마포구",
    "송파구",
    "서초구",
    "서울 전체",
    "경기도",
    "부산 전역",
    "성수",
    "합정",
    "을지로",
    "천호",
    "목동",
]
TIMES = [
    "오늘",
    "내일",
    "모레",
    "이번 주말",
    "금요일",
    "토요일 저녁",
    "9월 30일",
    "10월 3일",
    "저녁 7시",
    "오늘 밤",
    "내일 오후",
    "30일",
    "다음 주 수요일",
]
CHAINS = ["CGV", "롯데시네마", "메가박스"]
GENRES = [
    "코미디",
    "로맨스",
    "공포",
    "스릴러",
    "액션",
    "SF",
    "애니메이션",
    "다큐멘터리",
    "범죄",
    "판타지",
    "좀비",
    "사극",
    "뮤지컬",
    "전쟁",
    "재난",
    "하이틴",
    "느와르",
    "가족",
]
MOODS = [
    "비 오는 날 보기 좋은",
    "잠 안 올 때 볼",
    "울고 싶을 때 보는",
    "가볍게 웃을 수 있는",
    "머리 식히기 좋은",
    "연인이랑 보기 좋은",
    "혼자 보기 좋은",
    "주말에 몰아볼",
    "긴장감 넘치는",
    "여운이 남는",
]
ACTORS = [
    "송강호",
    "마동석",
    "전도연",
    "황정민",
    "톰 크루즈",
    "이병헌",
    "김혜수",
    "조인성",
    "틸다 스윈튼",
    "하정우",
]
PLOTS = [
    "주인공이 같은 하루를 계속 반복하는",
    "가난한 가족이 부잣집에 하나씩 취직하는",
    "기억을 잃은 남자가 범인을 쫓는",
    "시간 여행으로 과거를 바꾸려는",
    "외딴 섬에서 살아남는",
    "AI와 사랑에 빠지는",
    "은행 강도들이 한 팀이 되는",
    "좀비가 기차 안에 퍼지는",
    "우주에서 혼자 남겨진",
    "학교에서 벌어지는 괴담",
]
GENERAL = [
    "안녕",
    "안녕하세요",
    "ㅎㅇ",
    "고마워",
    "고마워요!",
    "넌 누구야?",
    "뭐 할 수 있어?",
    "오늘 기분 별로야",
    "배고프다",
    "심심해",
    "잘 자",
    "다음에 또 올게",
    "너 이름이 뭐야",
    "오늘 날씨 어때?",
    "ㅋㅋㅋ",
    "좋은 하루 보내",
    "도와줘서 고마워",
    "아 피곤하다",
]
FALLBACK_TITLES = [
    "인턴",
    "옵세션",
    "파과",
    "타짜",
    "기생충",
    "인셉션",
    "어벤져스",
    "파묘",
    "서울의 봄",
    "범죄도시",
]


# --- 한국어 조사 -----------------------------------------------------------------------------


def _has_batchim(word: str) -> bool | None:
    ch = word.strip()[-1:] if word.strip() else ""
    if not ("가" <= ch <= "힣"):
        return None  # 영문·숫자·기호로 끝나면 조사를 붙이지 않는다
    return (ord(ch) - 0xAC00) % 28 != 0


def josa(word: str, pair: str) -> str:
    """pair: "은는"|"이가"|"을를"|"으로로"(→ 로/으로)."""
    b = _has_batchim(word)
    if b is None:
        return word
    if pair == "으로로":
        last = word.strip()[-1]
        rieul = (ord(last) - 0xAC00) % 28 == 8
        return word + ("로" if (not b or rieul) else "으로")
    return word + (pair[0] if b else pair[1])


def ending(rng: random.Random, options: tuple[str, ...] = ("", "", "?", "요", "!")) -> str:
    return rng.choice(options)


# --- 대화 맥락(도우미 발화) — 운영 응답과 같은 문형 -----------------------------------------


def region_ask(t: str) -> str:
    return (
        f"『{t}』 상영관을 찾아드릴게요. 어느 지역에서 보실 계획인가요? "
        "이동수단까지 알려주시면 더 정확해요 (예: 강남 / 홍대입구역 차로 / 수원 도보)"
    )


def booking_result(t: str, r: str) -> str:
    return (
        f"『{t}』 — '{r}' 근처(반경 10km) 영화관 5곳을 가까운 순으로 찾았어요. "
        "롯데시네마 기준 오늘 상영 시간표 12회차를 찾았어요."
    )


def rec_reply(ts: list[str]) -> str:
    names = ", ".join(f"『{t}』" for t in ts)
    return f"이런 작품은 어떠세요? {names}를 골라봤어요."


def eval_reply(t: str) -> str:
    return f"『{t}』은(는) 관객 반응이 엇갈리지만 연출은 호평받았어요. mova 별점 4.1(리뷰 3건, 참고용)이에요."


# --- 패턴 생성기: (history, message, gold, pattern) ----------------------------------------


def p_booking_single(rng: random.Random, t: str) -> tuple:
    r = rng.choice(REGIONS)
    d = rng.choice(TIMES)
    c = rng.choice(CHAINS)
    forms = [
        (f"{t} 예매하고 싶어", gold("booking", t)),
        (f"{t} 예매할래{ending(rng)}", gold("booking", t)),
        (f"{t} 표 있어?", gold("booking", t)),
        (f"{t} 상영관 알려줘", gold("booking", t)),
        (f"{t} 어디서 볼 수 있어?", gold("booking", t)),
        (f"{josa(t, '을를')} 극장에서 보고 싶은데", gold("booking", t)),
        (f"{t} 시간표 보여줘", gold("booking", t)),
        (f"{josa(t, '은는')} 몇 시에 해?", gold("booking", t)),
        (f"{r}에서 {t} 예매하고 싶어", gold("booking", t, r)),
        (f"{r} 근처에서 {t} 몇 시에 해?", gold("booking", t, r)),
        (f"{t} {r}에서 볼 수 있어?", gold("booking", t, r)),
        (f"{d} {t} 몇 시에 해?", gold("booking", t, None, d)),
        (f"{r}에서 {t} {d} 몇 시에 볼 수 있어?", gold("booking", t, r, d)),
        (f"{c}에서 {t} 예매하려고", gold("booking", t, None, None, c)),
        (f"{r} {c}에서 {t} 시간표 알려줘", gold("booking", t, r, None, c)),
        (f"{d} {r} {c} {t} 자리 있어?", gold("booking", t, r, d, c)),
    ]
    msg, g = rng.choice(forms)
    return [], msg, g, "booking_single"


def p_booking_region_followup(rng: random.Random, t: str) -> tuple:
    r = rng.choice(REGIONS)
    msg = rng.choice(
        [
            r,
            f"{r}요",
            f"{r} 쪽",
            f"{r} 근처",
            f"{josa(r, '으로로')} 갈게",
            f"{r} 차로 갈게",
            f"{r} 도보",
            f"{r}에서 볼래",
        ]
    )
    hist = [
        {"role": "user", "content": f"{t} 예매하고 싶어"},
        {"role": "assistant", "content": region_ask(t)},
    ]
    return hist, msg, gold("booking", t, r, followup=True), "booking_region_followup"


def p_booking_date_followup(rng: random.Random, t: str) -> tuple:
    r = rng.choice(REGIONS)
    d = rng.choice(TIMES)
    msg = rng.choice(
        [
            f"{josa(d, '으로로')} 찾아줘",
            f"{josa(d, '은는')}?",
            f"{d}자로 다시 봐줘",
            f"{d} 걸로 알려줘",
            f"{d}에 볼래",
        ]
    )
    hist = [
        {"role": "user", "content": f"{t} 예매하고 싶어"},
        {"role": "assistant", "content": region_ask(t)},
        {"role": "user", "content": r},
        {"role": "assistant", "content": booking_result(t, r)},
    ]
    return hist, msg, gold("booking", t, None, d, followup=True), "booking_date_followup"


def p_booking_region_change(rng: random.Random, t: str) -> tuple:
    r1, r2 = rng.sample(REGIONS, 2)
    msg = rng.choice(
        [
            f"{josa(r2, '으로로')} 바꿔줘",
            f"{r2}에서도 찾아줘",
            f"{josa(r2, '은는')} 어때?",
            f"그럼 {r2} 쪽은?",
        ]
    )
    hist = [
        {"role": "user", "content": f"{r1}에서 {t} 예매하고 싶어"},
        {"role": "assistant", "content": booking_result(t, r1)},
    ]
    return hist, msg, gold("booking", t, r2, followup=True), "booking_region_change"


def p_booking_discovery(rng: random.Random, _t: str) -> tuple:
    r = rng.choice(REGIONS)
    forms = [
        ("지금 예매할 수 있는 영화 뭐 있어?", gold("booking")),
        ("요즘 극장에서 뭐 해?", gold("booking")),
        (f"{r}에서 지금 상영하는 영화 알려줘", gold("booking", None, r)),
        (f"{r} 근처 영화관 어디 있어?", gold("booking", None, r)),
        (f"{rng.choice(CHAINS)} 지금 뭐 상영해?", None),
    ]
    msg, g = rng.choice(forms)
    if g is None:
        c = next(c for c in CHAINS if c in msg)
        g = gold("booking", chain=c)
    return [], msg, g, "booking_discovery"


def p_evaluate(rng: random.Random, t: str) -> tuple:
    msg = rng.choice(
        [
            f"{t} 어때{ending(rng, ('', '?', '??'))}",
            f"{t} 볼만해?",
            f"{josa(t, '은는')} 재밌어?",
            f"{t} 평점 어때",
            f"{t} 리뷰 알려줘",
            f"{t} 줄거리 알려줘",
            f"{t} 무슨 내용이야?",
            f"{josa(t, '은는')} 어떤 영화야?",
            f"{t} 괜찮아?",
        ]
    )
    return [], msg, gold("evaluate", t), "evaluate"


def p_evaluate_after_rec(rng: random.Random, t: str, others: list[str]) -> tuple:
    genre = rng.choice(GENRES)
    shown = [t, *others[:2]]
    rng.shuffle(shown)
    hist = [
        {"role": "user", "content": f"{genre} 영화 추천해줘"},
        {"role": "assistant", "content": rec_reply(shown)},
    ]
    msg = rng.choice([f"{josa(t, '은는')} 어때?", f"{t} 줄거리 알려줘", f"{t} 평점은?"])
    return hist, msg, gold("evaluate", t), "evaluate_after_rec"


def p_evaluate_bare_followup(rng: random.Random, t: str) -> tuple:
    hist = [
        {"role": "user", "content": f"{t} 알아?"},
        {"role": "assistant", "content": eval_reply(t)},
    ]
    msg = rng.choice(["그거 어때?", "그 영화 볼만해?", "평점은?", "리뷰는 어때?", "어떠냐고"])
    return hist, msg, gold("evaluate", t, followup=True), "evaluate_bare_followup"


def p_eval_to_booking(rng: random.Random, t: str) -> tuple:
    r = rng.choice(REGIONS)
    hist = [
        {"role": "user", "content": f"{t} 어때"},
        {"role": "assistant", "content": eval_reply(t)},
    ]
    msg = rng.choice(
        [
            f"{r}쪽에 예매할 시간 있어?",
            f"{r}에서 볼 수 있어?",
            "예매하고 싶어",
            "그거 예매해줘",
            f"{r}에서 몇 시에 해?",
        ]
    )
    region = r if r in msg else None
    return hist, msg, gold("booking", t, region, followup=True), "eval_to_booking"


def p_choice(rng: random.Random, t: str) -> tuple:
    y1, y2 = sorted(rng.sample(range(1995, 2027), 2))
    hist = [
        {"role": "user", "content": f"{t} 어때"},
        {
            "role": "assistant",
            "content": f"비슷한 제목이 여러 편이에요: {t}({y1}) / {t}({y2}). 어떤 작품을 말씀하시나요?",
        },
    ]
    msg = rng.choice([f"{str(y2)[2:]}년꺼", f"{y2}년 거", "두번째", f"{y1}년 작품", "첫번째"])
    return hist, msg, gold("evaluate", t, followup=True), "choice"


def p_recommend(rng: random.Random, _t: str) -> tuple:
    forms = [
        f"{rng.choice(GENRES)} 영화 추천해줘",
        f"{rng.choice(MOODS)} 영화 추천해줘",
        f"{rng.choice(ACTORS)} 나오는 영화",
        f"{rng.choice(ACTORS)} {rng.choice(GENRES)} 영화 추천",
        f"{rng.choice(PLOTS)} 영화 찾아줘",
        f"{rng.choice(PLOTS)} 영화 있어?",
        f"요즘 볼만한 {rng.choice(GENRES)} 뭐 있어?",
        f"{rng.choice(['뭐 볼까?', '볼 거 추천 좀', '영화 하나 골라줘', '오늘 뭐 보지'])}",
        f"{rng.choice(['주말에', '퇴근하고', '가족이랑', '친구랑', '혼자'])} 볼 {rng.choice(GENRES)} 영화 추천해줘",
        f"{rng.choice(MOODS)} {rng.choice(GENRES)} 영화 있어?",
        f"{rng.choice(ACTORS)} 영화 중에 {rng.choice(MOODS)} 거",
        f"{rng.choice(['2000년대', '90년대', '최신', '클래식'])} {rng.choice(GENRES)} 영화 추천",
        f"넷플릭스에서 볼 만한 {rng.choice(GENRES)} 추천",
    ]
    return [], rng.choice(forms), gold("recommend"), "recommend"


def p_general(rng: random.Random, _t: str) -> tuple:
    msg = (
        rng.choice(["", "", "음 ", "아 ", "저기 "])
        + rng.choice(GENERAL)
        + rng.choice(["", "", "~", "!", " ㅎㅎ", " ㅠㅠ"])
    )
    return [], msg.strip(), gold("general"), "general"


PATTERNS: list[tuple[str, float]] = [
    ("booking_single", 0.20),
    ("booking_region_followup", 0.10),
    ("booking_date_followup", 0.07),
    ("booking_region_change", 0.05),
    ("booking_discovery", 0.04),
    ("evaluate", 0.12),
    ("evaluate_after_rec", 0.06),
    ("evaluate_bare_followup", 0.05),
    ("eval_to_booking", 0.06),
    ("choice", 0.04),
    ("recommend", 0.14),
    ("general", 0.07),
]


# --- 하드 체크 -------------------------------------------------------------------------------

_KEYS = ["intent", "title", "region", "time", "chain", "followup"]


def check(history: list[dict[str, str]], message: str, g: dict[str, Any]) -> str | None:
    """정답이 운영 규칙에 맞는지 — 어긋나면 사유, 맞으면 None."""
    if list(g) != _KEYS or g["intent"] not in {"recommend", "evaluate", "booking", "general"}:
        return "키·intent"
    context = message + " " + " ".join(m["content"] for m in history)
    if g["title"] and g["title"] not in context:
        return "title이 발화·대화에 없음"
    if g["title"] and not g["followup"] and g["title"] not in message:
        return "후속이 아닌데 title이 발화에 없음"
    if g["region"] and g["region"] not in message:
        return "region이 발화에 없음"
    if g["time"] and g["time"] not in message:
        return "time이 발화에 없음"
    if g["chain"] and g["chain"] not in message:
        return "chain이 발화에 없음"
    if g["followup"] and not history:
        return "대화 없이 followup"
    return None


# --- 평가셋: 하네스 장면 + 사람이 단 정답 -----------------------------------------------------

# eval_chat_multiturn.SCENES 순서와 1:1. 장면이 늘면 여기도 추가(개수 불일치면 즉시 실패).
_MULTITURN_GOLD = [
    gold("booking", "인턴"),
    gold("booking", "인턴", "군자", followup=True),
    gold("booking", "인턴"),
    gold("booking", "인턴"),
    gold("booking", None, "군자역"),
    gold("booking", "인턴", "군자", "오늘"),
    gold("booking", "옵세션", "군자역", followup=True),
    gold("evaluate", "옵세션"),
    gold("booking"),
    gold("booking", "옵세션", "군자", followup=True),
    gold("evaluate", "스파이더맨: 브랜드 뉴 데이", followup=True),
    gold("booking", "옵세션", "강남", followup=True),
    gold("booking", "옵세션", None, "9월 30일", followup=True),
    gold("booking", "옵세션", "서울 전체", followup=True),
    gold("booking", "인턴", "강남구", followup=True),
    gold("booking", "인 타임"),
]


def _harness_rows() -> list[dict[str, Any]]:
    """하네스 두 개에서 (history, message)를 읽는다. 스크립트 import가 막히면 ast로 상수만."""
    rows: list[dict[str, Any]] = []
    multi = _ast_eval_module_lists("eval_chat_multiturn", "SCENES")
    if len(multi) != len(_MULTITURN_GOLD):
        raise SystemExit(
            f"멀티턴 장면 {len(multi)}개 ≠ 정답 {len(_MULTITURN_GOLD)}개 — _MULTITURN_GOLD 갱신 필요"
        )
    for scene, g in zip(multi, _MULTITURN_GOLD, strict=True):
        rows.append(
            {
                "history": scene.get("history") or [],
                "message": scene["q"],
                "gold": g,
                "src": scene["name"],
            }
        )
    for q in _ast_eval_module_lists("eval_chat_queries", "QUERIES"):
        intent = "general" if q["q"] in {"안녕"} else "recommend"
        rows.append(
            {"history": [], "message": q["q"], "gold": gold(intent), "src": "single:" + q["q"]}
        )
    return rows


def _ast_eval_module_lists(module: str, name: str) -> list[dict[str, Any]]:
    """모듈 최상위의 문자열 상수와 name 리스트를 import 없이 평가한다(하네스는 httpx를 import한다)."""
    tree = ast.parse((_ROOT / "scripts" / f"{module}.py").read_text(encoding="utf-8"))
    env: dict[str, Any] = {}
    target: Any = None
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if not isinstance(tgt, ast.Name) or node.value is None:
                continue
            try:
                value = eval(compile(ast.Expression(node.value), module, "eval"), {}, env)  # noqa: S307
            except Exception:  # noqa: BLE001 — 함수 호출 등 평가 불가 상수는 건너뛴다
                continue
            env[tgt.id] = value
            if tgt.id == name:
                target = value
    if target is None:
        # eval_chat_queries의 리스트 이름이 다르면 dict 리스트 중 'q'를 가진 첫 리스트
        target = next(
            (
                v
                for v in env.values()
                if isinstance(v, list) and v and isinstance(v[0], dict) and "q" in v[0]
            ),
            [],
        )
    return target


# --- 메인 ------------------------------------------------------------------------------------


def _row(
    history: list[dict[str, str]], message: str, g: dict[str, Any], pattern: str
) -> dict[str, Any]:
    return {
        "system": SYSTEM_PROMPT,
        "prompt": render_prompt(message, history),
        "completion": completion(g),
        "pattern": pattern,
        "gold": g,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--n", type=int, default=1600, help="train+val 총 행 수")
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--out", type=Path, default=_OUT)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    titles = (
        [t.strip() for t in _TITLES.read_text(encoding="utf-8").splitlines() if t.strip()]
        if _TITLES.exists()
        else []
    )
    titles = [t for t in titles if "'" not in t and "『" not in t] or FALLBACK_TITLES
    # 운영에서 실제로 나온 제목은 가중(현재 상영작 대화가 많다)
    titles += FALLBACK_TITLES * 8

    eval_rows = _harness_rows()
    eval_keys = {(json.dumps(r["history"], ensure_ascii=False), r["message"]) for r in eval_rows}

    gens = {
        "booking_single": p_booking_single,
        "booking_region_followup": p_booking_region_followup,
        "booking_date_followup": p_booking_date_followup,
        "booking_region_change": p_booking_region_change,
        "booking_discovery": p_booking_discovery,
        "evaluate": p_evaluate,
        "evaluate_bare_followup": p_evaluate_bare_followup,
        "eval_to_booking": p_eval_to_booking,
        "choice": p_choice,
        "recommend": p_recommend,
        "general": p_general,
    }
    names = [p for p, _ in PATTERNS]
    weights = [w for _, w in PATTERNS]

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    rejected: Counter[str] = Counter()
    # 패턴별 할당량 — 가중 무작위는 표현 공간이 작은 패턴(잡담)이 중복 제거에 걸려 목표보다 모자랐다.
    for pat, w in zip(names, weights, strict=True):
        quota = round(args.n * w)
        made = 0
        for _ in range(quota * 40):
            if made >= quota:
                break
            t = rng.choice(titles)
            if pat == "evaluate_after_rec":
                hist, msg, g, pname = p_evaluate_after_rec(rng, t, rng.sample(titles, 2))
            else:
                hist, msg, g, pname = gens[pat](rng, t)
            key = (json.dumps(hist, ensure_ascii=False), msg)
            if key in seen or key in eval_keys:
                continue
            reason = check(hist, msg, g)
            if reason:
                rejected[reason] += 1
                continue
            seen.add(key)
            rows.append(_row(hist, msg, g, pname))
            made += 1
        if made < quota:
            print(f"⚠ {pat}: 할당 {quota} 중 {made}행만 생성(표현 공간 부족)")

    rng.shuffle(rows)
    n_val = max(1, len(rows) // 10)
    val, train = rows[:n_val], rows[n_val:]
    evals = [_row(r["history"], r["message"], r["gold"], "harness:" + r["src"]) for r in eval_rows]
    bad_eval = [r["pattern"] for r in eval_rows if check(r["history"], r["message"], r["gold"])]

    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in (("train", train), ("val", val), ("eval", evals)):
        with (args.out / f"understanding_{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dist = Counter(r["pattern"] for r in rows)
    intents = Counter(r["gold"]["intent"] for r in rows)
    print(f"train {len(train)} · val {len(val)} · eval {len(evals)}(하네스)  → {args.out}")
    print("패턴:", dict(sorted(dist.items(), key=lambda kv: -kv[1])))
    print("intent:", dict(intents))
    print("followup 비율: %.0f%%" % (100 * sum(r["gold"]["followup"] for r in rows) / len(rows)))
    if rejected:
        print("하드 체크 탈락:", dict(rejected))
    if bad_eval:
        print("⚠ 평가셋 정답이 규칙과 어긋남:", bad_eval)


if __name__ == "__main__":
    main()
