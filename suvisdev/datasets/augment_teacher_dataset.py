"""교사 데이터셋(chat_teacher_dataset.jsonl) 증강 — 원본 1건당 변형 3건을 더한다.

- shuffle   : 카탈로그 줄 순서만 섞음(위치가 아니라 내용으로 고르게)
- para1/2   : Gemini가 사용자 발화를 조건 보존·말투만 바꿔 다시 씀 + 카탈로그 섞음
completion(정답 픽)은 원본 그대로 둔다 — 조건이 같으니 정답도 같다.

각 행에 src(원본 인덱스)·aug(변형 종류)를 붙인다. 코랩 노트북은 src 기준으로
평가셋을 떼어내 증강본이 학습·평가에 섞이지 않게 한다(train 스크립트는 여분 키 무시).

프로젝트 모듈(fastapi 등) 의존 없이 google-genai·python-dotenv만 필요하다.

Usage (suvisdev/에서, .env의 GEMINI_API_KEY 사용):
  python datasets/augment_teacher_dataset.py
출력: datasets/chat_teacher_dataset_aug.jsonl, 재개용 캐시 datasets/.paraphrase_cache.json
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]

SRC = _BACKEND / "datasets" / "chat_teacher_dataset.jsonl"
OUT = _BACKEND / "datasets" / "chat_teacher_dataset_aug.jsonl"
CACHE = _BACKEND / "datasets" / ".paraphrase_cache.json"
SLEEP_SECONDS = 4.5  # Gemini 무료 티어 15req/min
MODEL = "gemini-3.1-flash-lite"  # keymaker 기본값과 동일

# 개수 조건이 붙은 패러프레이즈는 정답(최대 3편)과 모순되므로 버린다
_COUNT_RE = re.compile(r"하나|한 ?편|한 ?개|두 ?편|세 ?편|몇 ?편|몇 ?개")
_USER_RE = re.compile(r"<<<USER_INPUT>>>(.*?)<<<END_USER_INPUT>>>", re.S)

_PARA_PROMPT = """영화 추천 챗봇에 사용자가 보낸 메시지를 다른 사람이 쓴 것처럼 2가지로 바꿔 쓰세요.

규칙:
- 장르·분위기·배우·국가·연도 등 조건은 그대로 유지하고, 새 조건을 더하거나 빼지 마세요.
- 둘은 말투가 서로 달라야 합니다(예: 짧은 반말 / 공손한 존댓말 / 구어체 질문).
- "하나만", "한 편", "몇 개" 같은 개수 표현은 넣지 마세요(정답 편수가 달라짐).
- 각 40자 이내, 원문과 똑같이 쓰지 마세요.

원문: {query}

JSON 배열 한 줄만 출력: ["...", "..."]"""


def _shuffle_catalog(prompt: str, rng: random.Random) -> str:
    lines = prompt.split("\n")
    idx = [i for i, line in enumerate(lines) if line.startswith("- movie_id=")]
    items = [lines[i] for i in idx]
    rng.shuffle(items)
    for i, item in zip(idx, items, strict=True):
        lines[i] = item
    return "\n".join(lines)


def _replace_user(prompt: str, new_query: str) -> str:
    """실제 발화는 마지막 구분자 쌍이다(앞쪽은 규칙 설명문 속 구분자 언급)."""
    m = list(_USER_RE.finditer(prompt))[-1]
    return prompt[: m.start(1)] + new_query + prompt[m.end(1) :]


def _paraphrase(query: str, client) -> list[str]:
    raw = client.models.generate_content(model=MODEL, contents=_PARA_PROMPT.format(query=query)).text
    start, end = raw.find("["), raw.rfind("]")
    items = json.loads(raw[start : end + 1])
    out = [s.strip() for s in items if isinstance(s, str)]
    return [s for s in out if s and s != query and len(s) <= 60]


def main() -> None:
    from dotenv import load_dotenv
    from google import genai

    load_dotenv(_BACKEND / ".env")
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    rows = [json.loads(line) for line in SRC.open(encoding="utf-8") if line.strip()]
    cache: dict[str, list[str]] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rng = random.Random(20260917)
    out: list[dict] = []

    for i, row in enumerate(rows):
        prompt, completion = row["prompt"], row["completion"]
        query = _USER_RE.findall(prompt)[-1]
        out.append({"prompt": prompt, "completion": completion, "src": i, "aug": "orig"})
        out.append(
            {
                "prompt": _shuffle_catalog(prompt, rng),
                "completion": completion,
                "src": i,
                "aug": "shuffle",
            }
        )

        if query not in cache:
            try:
                cache[query] = _paraphrase(query, client)
            except Exception as e:  # noqa: BLE001 — 한 건 실패해도 나머지는 진행
                print(f"[{i + 1}/{len(rows)}] 패러프레이즈 실패: {query} | {e}")
                cache[query] = []
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            time.sleep(SLEEP_SECONDS)
        paras = [p for p in cache[query] if not _COUNT_RE.search(p)][:2]
        for k, para in enumerate(paras, start=1):
            out.append(
                {
                    "prompt": _shuffle_catalog(_replace_user(prompt, para), rng),
                    "completion": completion,
                    "src": i,
                    "aug": f"para{k}",
                }
            )
        print(f"[{i + 1}/{len(rows)}] {query} → {paras}", flush=True)

    with OUT.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[aug] 원본 {len(rows)}건 → {len(out)}건: {OUT}")


if __name__ == "__main__":
    main()
