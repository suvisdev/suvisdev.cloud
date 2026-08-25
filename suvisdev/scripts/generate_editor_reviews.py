"""에디터 리뷰 수동 실행 래퍼 — 로직은 스케줄러 모듈과 단일 경로를 공유한다.

상시 자동 생성은 main.py lifespan의 run_editor_reviews_scheduler(24시간 주기,
EDITOR_REVIEWS_DAILY_LIMIT 기본 15편)가 담당하고, 이 스크립트는 즉시 1회
돌리고 싶을 때 쓴다.

Usage (backend 컨테이너 안):
  docker exec suvisdevcloud-backend-1 python scripts/generate_editor_reviews.py --limit 20
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t%(message)s")

if __name__ == "__main__":
    from mova.adapter.inbound.scheduler.editor_reviews_scheduler import (
        generate_editor_reviews_once,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()
    created, total = asyncio.run(generate_editor_reviews_once(args.limit))
    print(f"DONE — 생성 {created} / 대상 {total}")
