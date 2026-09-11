"""RS 교사 루프 1단계 — 프로덕션 chats에서 실사용 질의를 채굴한다 (2026-09-11).

chats.raw_message에서 추천 학습에 쓸 만한 사용자 발화를 추려 JSONL로 쓴다.
빈도순 정렬(자주 묻는 질의가 데이터셋에 먼저 들어가게)·중복 제거·길이 필터.
예매/평가 트랙 어휘가 든 발화는 제외한다 — LoRA의 역할은 recommend 트랙
생성뿐이고, 흐름 제어는 코드가 담당한다(설계 원칙).

Usage:
  # 프로덕션(노트북): kubectl -n suvisdev exec deploy/backend -- \
  #   python scripts/rs_mine_queries.py --out datasets/rs_queries.jsonl
  # 로컬 개발 DB: python scripts/rs_mine_queries.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(_BACKEND), str(_BACKEND / "apps")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_MIN_LEN, _MAX_LEN = 4, 60
# recommend 외 트랙·잡담 신호 — 이 어휘가 있으면 제외
_EXCLUDE = re.compile(
    r"예매|예약|티켓|표\s*끊|상영|극장|영화관|시간표"  # booking
    r"|어때|어떄|평가|평점|리뷰|볼만해"  # evaluate
    r"|안녕|고마워|ㅋㅋ|ㅎㅎ|hi|hello"  # 잡담
)
_HANGUL = re.compile(r"[가-힣]")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(_BACKEND / "datasets" / "rs_queries.jsonl"))
    parser.add_argument("--limit", type=int, default=300, help="상위 N개 질의")
    parser.add_argument("--days", type=int, default=90, help="최근 N일 발화만")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker

    get_keymaker()  # .env 로드 부작용 — DB URL 주입
    factory = get_mova_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    "select raw_message from chats "
                    "where created_at > now() - make_interval(days => :days)"
                ),
                {"days": args.days},
            )
        ).all()

    counter: Counter[str] = Counter()
    for (raw,) in rows:
        msg = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not (_MIN_LEN <= len(msg) <= _MAX_LEN):
            continue
        if not _HANGUL.search(msg) or _EXCLUDE.search(msg):
            continue
        counter[msg] += 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for query, count in counter.most_common(args.limit):
            f.write(json.dumps({"query": query, "count": count}, ensure_ascii=False) + "\n")
    print(
        f"[rs-mine] 원발화 {len(rows)}건 → 고유 질의 {len(counter)}건 → 상위 "
        f"{min(args.limit, len(counter))}건 저장: {out}"
    )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
