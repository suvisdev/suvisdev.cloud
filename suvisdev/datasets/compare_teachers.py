"""교사 모델 비교 — 같은 프롬프트에 대한 Gemini(무료 티어, v4 캐시의 원문) vs Claude Haiku 응답을
하드 체크(노트북 3-2와 동일 규칙)와 블라인드 심판(Claude Opus 5, A/B 순서 무작위)으로 비교한다.
실측 토큰 사용량으로 비용도 같이 낸다(추정이 아니라 usage 값).

  ~/.venv/bin/python datasets/compare_teachers.py --n 30
환경: ANTHROPIC_API_KEY(suvisdev/.env), 바탕화면 v4 데이터셋 + datasets/.v4_cache.json(Gemini 원문).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from pathlib import Path

import anthropic

_D = Path(__file__).resolve().parent
_V4 = Path("/mnt/c/Users/suteagy/Desktop/mova/FT/mova-colab-v4/chat_teacher_dataset_v4.jsonl")
_GEMINI_CACHE = _D / ".v4_cache.json"
_OUT = _D / "teacher_compare_20260923.json"
GEN_MODEL = "claude-haiku-4-5"
JUDGE_MODEL = "claude-opus-5"
PRICE = {  # $/1M, claude-api 스킬 표(2026-06 캐시)
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-opus-5": (5.0, 25.0),
}

CAT_RE = re.compile(
    r"^- movie_id=(\d+) (.+?) \((?:\d{4}|연도 미상)\)(?: \[[^\]]*\])*(?: — 줄거리: .*)?$", re.M
)
USER_RE = re.compile(r"<<<USER_INPUT>>>(.*?)<<<END_USER_INPUT>>>", re.S)
HANJA_RE = re.compile(r"[一-鿿]")
YEAR_TAIL = re.compile(r"\s*\(\d{4}\)\s*$")
JUDGE_PROMPT = """당신은 영화 추천 챗봇 응답의 심사위원입니다. 같은 요청에 대한 두 응답 A와 B를 비교하세요.

채점 기준(중요한 순):
1. 그라운딩 — 카탈로그 안의 작품만, 질의 조건(장르·분위기·배우·연도)에 실제로 맞는 픽인가
2. intro 말투 — 존댓말, 1~2문장, 과장·확신 남발 금지, 자연스러운 한국어
3. hook — 각 픽의 한 줄 어필이 구체적이고 스포일러 없이 매력적인가(40자 이내)
4. 정직성 — 맞는 작품이 부족하면 억지로 채우지 않는가, 인사·잡담에는 추천하지 않는가
형식(JSON만 출력) 위반은 크게 감점하세요.

[사용자 질의]
{query}

[카탈로그]
{catalog}

[응답 A]
{a}

[응답 B]
{b}

JSON 한 줄만 출력:
{{"score_a": <0~10>, "score_b": <0~10>, "winner": "A" 또는 "B" 또는 "tie", "reason": "<한 문장>"}}"""


def catalog(prompt: str) -> dict[int, str]:
    return {int(m[1]): m[2] for m in CAT_RE.finditer(prompt)}


def parse(raw: str) -> dict | None:
    s, e = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[s : e + 1])
    except ValueError:
        return None


def _mid(p: dict):
    try:
        return int(p.get("movie_id"))
    except (TypeError, ValueError):
        return None


def hard_check(raw: str, prompt: str) -> dict[str, bool]:
    cat, d = catalog(prompt), parse(raw)
    ok = (
        isinstance(d, dict)
        and isinstance(d.get("picks"), list)
        and bool(str(d.get("intro", "")).strip())
    )
    picks = d["picks"] if ok else []
    ok = ok and all(isinstance(p, dict) for p in picks)
    r = {"json": ok}
    r["grounded"] = ok and all(_mid(p) in cat for p in picks)
    r["title"] = r["grounded"] and all(
        YEAR_TAIL.sub("", str(p.get("title", ""))).strip() == cat[_mid(p)] for p in picks
    )
    r["hook40"] = ok and all(len(str(p.get("hook", ""))) <= 40 for p in picks)
    r["max3"] = ok and len(picks) <= 3
    r["empty_ok"] = ok and (bool(cat) or not picks)
    r["no_hanja"] = not HANJA_RE.search(raw)
    r["pass"] = all(r.values())
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20260923)
    args = ap.parse_args()

    rows = [json.loads(ln) for ln in _V4.open(encoding="utf-8") if ln.strip()]
    cache = json.loads(_GEMINI_CACHE.read_text(encoding="utf-8"))
    pool = [r for r in rows if hashlib.sha1(r["prompt"].encode()).hexdigest() in cache]
    sample = random.Random(args.seed).sample(pool, min(args.n, len(pool)))
    print(f"Gemini 원문이 있는 프롬프트 {len(pool)}행 중 {len(sample)}행 비교")

    client = anthropic.Anthropic()
    usage = {GEN_MODEL: [0, 0], JUDGE_MODEL: [0, 0]}
    flip = random.Random(args.seed)
    results = []
    for i, r in enumerate(sample, 1):
        prompt = r["prompt"]
        query = USER_RE.findall(prompt)[-1]
        gem = cache[hashlib.sha1(prompt.encode()).hexdigest()]
        msg = client.messages.create(
            model=GEN_MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
        )
        hk = "".join(b.text for b in msg.content if b.type == "text")
        usage[GEN_MODEL][0] += msg.usage.input_tokens
        usage[GEN_MODEL][1] += msg.usage.output_tokens

        swap = flip.random() < 0.5
        a, b = (hk, gem) if swap else (gem, hk)
        cat = "\n".join(f"- {k}: {v}" for k, v in catalog(prompt).items()) or "(비어 있음)"
        jm = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": JUDGE_PROMPT.format(query=query, catalog=cat, a=a, b=b)}
            ],
        )
        usage[JUDGE_MODEL][0] += jm.usage.input_tokens
        usage[JUDGE_MODEL][1] += jm.usage.output_tokens
        d = parse("".join(b.text for b in jm.content if b.type == "text")) or {}
        try:
            sa, sb = float(d["score_a"]), float(d["score_b"])
        except (KeyError, TypeError, ValueError):
            sa = sb = None
        w = str(d.get("winner", "tie"))
        winner = {"A": "haiku" if swap else "gemini", "B": "gemini" if swap else "haiku"}.get(
            w, "tie"
        )
        g_score, h_score = ((sb, sa) if swap else (sa, sb)) if sa is not None else (None, None)
        results.append(
            {
                "query": query,
                "gemini": gem,
                "haiku": hk,
                "checks": {"gemini": hard_check(gem, prompt), "haiku": hard_check(hk, prompt)},
                "judge": {
                    "gemini": g_score,
                    "haiku": h_score,
                    "winner": winner,
                    "reason": d.get("reason", ""),
                },
            }
        )
        print(
            f"[{i}/{len(sample)}] {query[:30]} | 심판 gemini {g_score} vs haiku {h_score} → {winner}",
            flush=True,
        )
        time.sleep(0.5)

    keys = ["pass", "json", "grounded", "title", "hook40", "max3", "empty_ok", "no_hanja"]
    print("\n■ 하드 체크 통과율")
    print(f"{'':8}" + "".join(f"{k:>10}" for k in keys))
    summary = {"hard": {}, "judge": {}, "usage": {}, "cost_usd": {}}
    for s in ("gemini", "haiku"):
        rates = {k: sum(x["checks"][s][k] for x in results) / len(results) for k in keys}
        summary["hard"][s] = rates
        print(f"{s:8}" + "".join(f"{rates[k]:>10.0%}" for k in keys))
    js = [x["judge"] for x in results if x["judge"]["gemini"] is not None]
    summary["judge"] = {
        "gemini_avg": round(sum(j["gemini"] for j in js) / len(js), 2),
        "haiku_avg": round(sum(j["haiku"] for j in js) / len(js), 2),
        "gemini_win": sum(j["winner"] == "gemini" for j in js),
        "tie": sum(j["winner"] == "tie" for j in js),
        "haiku_win": sum(j["winner"] == "haiku" for j in js),
        "judged": len(js),
    }
    print(f"\n■ 블라인드 심판({JUDGE_MODEL}): {summary['judge']}")
    for m, (inp, out) in usage.items():
        cost = inp / 1e6 * PRICE[m][0] + out / 1e6 * PRICE[m][1]
        summary["usage"][m] = {"input": inp, "output": out}
        summary["cost_usd"][m] = round(cost, 4)
        print(
            f"■ {m}: 입력 {inp:,} · 출력 {out:,} 토큰 → ${cost:.4f} (행당 ${cost / len(results):.5f})"
        )
    _OUT.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"저장: {_OUT}")


if __name__ == "__main__":
    main()
