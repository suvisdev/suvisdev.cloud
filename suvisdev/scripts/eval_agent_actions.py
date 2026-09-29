"""판단 단계 평가셋(agent_eval.jsonl)을 Ollama 모델로 채점 — 기준선(7.8B·4.0 1.2B)과 학습한 v9 GGUF 비교.

Usage (suvisdev 폴더, ~/.venv-exaone/bin/python):
  python scripts/eval_agent_actions.py exaone3.5:7.8b
  python scripts/eval_agent_actions.py hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF:Q5_K_M --cpu
  python scripts/eval_agent_actions.py mova-agent-v9 --cpu --show 20

채점 규칙은 build_agent_dataset.match — 도구 이름 + 정답 인자(title·region·date) 정규화 일치, query는
비어 있지 않으면 통과, 정답에 없는 title·region을 지어 넣으면 실패. 코랩 노트북과 같은 함수다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
import build_agent_dataset as B  # noqa: E402, N812

AP = B.AP
_OLLAMA = "http://localhost:11434"


def ask(model: str, system: str, prompt: str, *, cpu: bool) -> str:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 120,
            "num_ctx": 4096,
            **({"num_gpu": 0} if cpu else {}),
        },
        "keep_alive": "10m",
    }
    r = httpx.post(f"{_OLLAMA}/api/chat", json=body, timeout=300)
    r.raise_for_status()
    return (r.json().get("message") or {}).get("content") or ""


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("model")
    ap.add_argument("--eval", type=Path, default=_ROOT / "datasets/agent/agent_eval.jsonl")
    ap.add_argument("--cpu", action="store_true", help="num_gpu 0 (운영 GPU를 건드리지 않는다)")
    ap.add_argument("--show", type=int, default=12, help="실패 사례 표시 수")
    ap.add_argument("--only", default=None, help="pattern 부분 문자열 필터")
    args = ap.parse_args()

    rows = [json.loads(line) for line in args.eval.open(encoding="utf-8") if line.strip()]
    if args.only:
        rows = [r for r in rows if args.only in r["pattern"]]
    ok, bad_format, by_src, fails = 0, 0, Counter(), []
    lat = []
    for r in rows:
        t0 = time.time()
        raw = ask(args.model, r["system"], r["prompt"], cpu=args.cpu)
        lat.append(time.time() - t0)
        pred = AP.parse_action(raw)
        hit = B.match(pred, r["gold"])
        src = r["pattern"].split(":")[0]
        by_src[src + ("_ok" if hit else "_n")] += 1
        if pred is None:
            bad_format += 1
        if hit:
            ok += 1
        else:
            fails.append((r, raw, pred))
    print(
        f"{args.model}: {ok}/{len(rows)} · 형식 실패 {bad_format} · 평균 {sum(lat) / len(lat):.1f}s"
    )
    srcs = sorted({k.rsplit("_", 1)[0] for k in by_src})
    print(
        "  "
        + " · ".join(
            f"{s} {by_src[s + '_ok']}/{by_src[s + '_ok'] + by_src[s + '_n']}" for s in srcs
        )
    )
    for r, raw, pred in fails[: args.show]:
        msg = r["prompt"].split("[발화]\n")[-1].split("\n")[0][:40]
        print(
            f"  ✗ {msg!r}\n     예측 {(json.dumps(pred, ensure_ascii=False) if pred else raw.strip()[:120])}\n     정답 {r['completion']}"
        )


if __name__ == "__main__":
    main()
