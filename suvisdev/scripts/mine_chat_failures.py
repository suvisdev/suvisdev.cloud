"""mova 채팅 실패 후보 채굴 — 규칙 판정으로 "맥락을 놓친 턴"을 모은다(API 비용 0).

사용자가 직접 써 보고 "멍청하다"고 알려 주기 전에 실패를 먼저 찾기 위한 1단계(2026-09-28).
모은 후보는 사람이(또는 Claude가) 이해 실패(→ 이해 모델 학습 데이터)와 코드 실패(→ 수정)로
나누고, 전부 `eval_chat_multiturn.py` 장면 후보가 된다.

입력 두 가지:
  - chat_messages(로그인 사용자 대화 — 응답·카드까지 있음)
  - datasets/understanding/shadow_log.jsonl(익명 포함 — 발화·히스토리·7.8B/v6 이해 결과, 응답은 없음)

규칙(`detect_turn`):
  zero_with_context   앞 대화에 작품이 나왔는데 0건/못 찾음 응답 — 맥락 유실 가능성이 가장 높다
  zero_result         맥락 없이 0건/못 찾음 응답
  reask_with_context  "그거·최신·두번째" 같은 지시어 발화에 앞 대화 작품이 있는데 "어떤 작품" 되물음
  user_correction     다음 사용자 발화가 "아니·말고·다시"로 시작하거나 거의 같은 말의 반복
  shadow_diff         7.8B와 v6 이해 결과가 다름(어느 쪽이 맞는지는 사람이 본다)

Usage (backend 파드 안에서 — datasets/는 hostPath라 결과가 노트북에 남는다):
  kubectl -n suvisdev exec deploy/backend -- python scripts/mine_chat_failures.py --days 7
  python scripts/mine_chat_failures.py --no-db      # 섀도 로그만(DB 없이)
출력: datasets/understanding/failures/failures_YYYYMMDD.jsonl + 규칙별 요약(stdout)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_DATASETS = _BACKEND / "datasets" / "understanding"
_HISTORY_KEEP = 4

# 0건 안내 풀(market_chat_interactor._zero_result_reply)·booking/evaluate의 "못 찾음" 문구.
ZERO_RE = re.compile(
    r"못 찾았|찾지 못했|카탈로그에 (?:없|안 남)|안 잡히|새 후보가 안|딱 맞는 게 없"
)
REASK_RE = re.compile(r"어떤 작품을|제목을 알려")
DEICTIC_RE = re.compile(
    r"그거|그것|그 영화|그중|거기서|[첫두세네]\s?번째|마지막|최신|최근|걔|이거|저거|아까"
)
CORRECTION_RE = re.compile(r"^\s*(?:아니|그게 아니|말고|다시|내 말은|그거 말고)")
TITLE_RE = re.compile(r"『[^』]+』")
_REPEAT_RATIO = 0.75


def history_has_title(history: list[dict[str, str]]) -> bool:
    return any(TITLE_RE.search(m.get("content") or "") for m in history)


def detect_turn(
    history: list[dict[str, str]],
    message: str,
    reply: str,
    next_user: str | None,
) -> list[str]:
    """한 턴(히스토리·발화·응답·다음 사용자 발화)에 걸린 규칙 이름들."""
    rules: list[str] = []
    context = history_has_title(history)
    if ZERO_RE.search(reply):
        rules.append("zero_with_context" if context else "zero_result")
    if context and REASK_RE.search(reply) and DEICTIC_RE.search(message):
        rules.append("reask_with_context")
    if next_user and (
        CORRECTION_RE.search(next_user)
        or SequenceMatcher(None, message.strip(), next_user.strip()).ratio() >= _REPEAT_RATIO
    ):
        rules.append("user_correction")
    return rules


def render_assistant(content: str, meta: dict[str, Any]) -> str:
    """프론트가 보내는 히스토리와 같은 모양 — 카드가 있으면 `[추천 카드] 1.『A』(2007) …`를 앞에."""
    recs = meta.get("recommendations") or []
    if not recs:
        return content
    cards = " ".join(
        f"{i}.『{r.get('title')}』" + (f"({r['year']})" if r.get("year") else "")
        for i, r in enumerate(recs, 1)
    )
    return f"[추천 카드] {cards}\n{content}"


def mine_conversation(
    conversation_id: int, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """한 대화의 메시지(시간순) → 실패 후보들. user 다음 assistant가 한 턴이다."""
    out: list[dict[str, Any]] = []
    history: list[dict[str, str]] = []
    users = [i for i, r in enumerate(rows) if r["role"] == "user"]
    for n, i in enumerate(users):
        user = rows[i]
        has_reply = i + 1 < len(rows) and rows[i + 1]["role"] == "assistant"
        reply_row = rows[i + 1] if has_reply else None
        reply = reply_row["content"] if reply_row else ""
        meta = (reply_row or {}).get("meta") or {}
        next_user = rows[users[n + 1]]["content"] if n + 1 < len(users) else None
        rules = detect_turn(history, user["content"], reply, next_user)
        if rules:
            out.append(
                {
                    "source": "conversation",
                    "rules": rules,
                    "conversation_id": conversation_id,
                    "at": str(user.get("created_at") or ""),
                    "message": user["content"],
                    "history": history[-_HISTORY_KEEP:],
                    "intent_type": (user.get("meta") or {}).get("intent_type"),
                    "reply": reply[:300],
                    "cards": [r.get("title") for r in meta.get("recommendations") or []],
                    "next_user": next_user,
                }
            )
        history.append({"role": "user", "content": user["content"]})
        if reply_row:
            history.append({"role": "assistant", "content": render_assistant(reply, meta)})
    return out


def mine_shadow(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source": "shadow",
            "rules": ["shadow_diff"],
            "trace_id": r.get("trace_id"),
            "message": r.get("message"),
            "history": r.get("history") or [],
            "diff": r.get("diff"),
            "primary": r.get("primary"),
            "shadow": r.get("shadow"),
            "shadow_error": r.get("shadow_error"),
        }
        for r in records
        if not r.get("match")
    ]


def _read_shadow(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


async def _load_conversations(days: int) -> dict[int, list[dict[str, Any]]]:
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory, reload_env

    reload_env()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    sql = text(
        "SELECT conversation_id, role, content, meta, created_at FROM chat_messages "
        "WHERE conversation_id IN (SELECT DISTINCT conversation_id FROM chat_messages "
        "WHERE created_at >= :since) ORDER BY conversation_id, created_at, id"
    )
    grouped: dict[int, list[dict[str, Any]]] = {}
    async with get_mova_session_factory()() as session:
        for row in (await session.execute(sql, {"since": since})).mappings():
            grouped.setdefault(row["conversation_id"], []).append(dict(row))
    return grouped


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--days", type=int, default=7, help="최근 N일 안에 메시지가 있는 대화(기본 7)")
    p.add_argument("--shadow", type=Path, default=_DATASETS / "shadow_log.jsonl")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--no-db", action="store_true", help="DB를 읽지 않고 섀도 로그만")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    failures: list[dict[str, Any]] = []
    n_conv = 0
    if not args.no_db:
        conversations = asyncio.run(_load_conversations(args.days))
        n_conv = len(conversations)
        for cid, rows in conversations.items():
            failures += mine_conversation(cid, rows)
    shadow = _read_shadow(args.shadow)
    failures += mine_shadow(shadow)

    out = args.out or _DATASETS / "failures" / f"failures_{datetime.now():%Y%m%d}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in failures:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    counts = Counter(rule for r in failures for rule in r["rules"])
    print(f"대화 {n_conv}건 · 섀도 {len(shadow)}건 검사 → 실패 후보 {len(failures)}건 ({out})")
    for rule, n in counts.most_common():
        print(f"  {rule:20} {n}")
    for r in failures[:10]:
        print(f"  - [{','.join(r['rules'])}] {r['message']!r}")


if __name__ == "__main__":
    main()
