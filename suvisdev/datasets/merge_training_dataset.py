"""학습용 데이터셋 병합 — 단일턴 증강본 + 멀티턴 후속턴 (2026-09-22).

병합하면서 정답의 title을 카탈로그 값으로 맞춘다. movie_id는 맞는데 제목만
교사가 잘못 쓴 행이 있다(09-17 데이터의 "슈리오 마리오 브라더스" 등 5행).
앱은 제목을 DB 값으로 덮어쓰므로 서빙에는 영향이 없지만, 학습 데이터에 오타를
남기면 모델이 그 표기를 배운다.

Usage (suvisdev/에서):
  python datasets/merge_training_dataset.py
출력: datasets/chat_teacher_dataset_20260922.jsonl
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_D = Path(__file__).resolve().parent
# v2(09-22) = 단일턴 증강 + 멀티턴. v3는 여기에 정직한 부족 안내·배우 질의를 더한다.
_V2 = [_D / "chat_teacher_dataset_aug.jsonl", _D / "chat_teacher_dataset_multiturn.jsonl"]
_V3_ADD = _D / "chat_teacher_dataset_v3_add.jsonl"

SRCS = _V2 + ([_V3_ADD] if _V3_ADD.exists() else [])
OUT = _D / ("chat_teacher_dataset_v3.jsonl" if _V3_ADD.exists() else "chat_teacher_dataset_20260922.jsonl")

_CAT_RE = re.compile(r"^- movie_id=(\d+) (.+?) \[.+?\]$", re.M)
_YEAR_TAIL_RE = re.compile(r"\s*\(\d{4}\)\s*$")


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", _YEAR_TAIL_RE.sub("", title)).strip()


def main() -> None:
    fixed = 0
    with OUT.open("w", encoding="utf-8") as out:
        for src in SRCS:
            for line in src.open(encoding="utf-8"):
                if not line.strip():
                    continue
                row = json.loads(line)
                catalog = {int(mid): t for mid, t in _CAT_RE.findall(row["prompt"])}
                data = json.loads(row["completion"])
                for pick in data.get("picks", []):
                    want = catalog.get(pick.get("movie_id"))
                    if want and _norm(pick.get("title", "")) != _norm(want):
                        pick["title"] = want
                        fixed += 1
                row["completion"] = json.dumps(data, ensure_ascii=False)
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
    total = sum(1 for _ in OUT.open(encoding="utf-8"))
    print(f"[merge] {total}행 → {OUT} (제목 교정 {fixed}건)")


if __name__ == "__main__":
    main()
