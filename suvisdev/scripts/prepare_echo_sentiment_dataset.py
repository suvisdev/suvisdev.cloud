"""Echo(감성 분석 에이전트, 07_sentiment_analysis) QLoRA 학습용 데이터셋 준비 1회 스크립트.

NSMC(Naver Sentiment Movie Corpus, https://github.com/e9t/nsmc)의 원본 TSV를
raw.githubusercontent.com에서 내려받아, EXAONE-3.5-2.4B-Instruct QLoRA
instruction-tuning 포맷(dataset/{train,val}.jsonl, {"instruction","input","output"})
으로 변환한다. mova가 영화 앱이라 도메인이 정확히 맞는다.

라벨(0=부정,1=긍정)만 그대로 "긍정"/"부정" 텍스트로 매핑한다 — NSMC 원본에는
근거 문장이 없어 "이유" 설명은 넣지 않는다(넣으려면 별도로 LLM 생성이 필요,
사용자 확인 후 스킵하기로 결정, 2026-07-22).

클래스 균형을 맞춰 라벨당 동일 개수를 뽑고, seed=42로 고정 셔플·분할한다.

Usage (suvisdev 폴더에서):
  python scripts/prepare_echo_sentiment_dataset.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import httpx

_APPS = Path(__file__).resolve().parents[1] / "apps"
_OUT_ROOT = _APPS / "ontology" / "resources" / "echo_sentiment_train"

_SEED = 42
_PER_LABEL_TRAIN = 1000  # 라벨당 학습 샘플 수 (총 2000, doc 권장 500~5000 안)
_PER_LABEL_VAL = 200  # 라벨당 검증 샘플 수 (총 400)
_MIN_CHARS = 5  # 너무 짧은 리뷰(의미 없는 리뷰) 제외

_LABEL_TEXT = {"0": "부정", "1": "긍정"}
_INSTRUCTION = "다음 영화 리뷰의 감정을 분석해줘."

_SOURCES = {
    "train": "https://raw.githubusercontent.com/e9t/nsmc/master/ratings_train.txt",
    "test": "https://raw.githubusercontent.com/e9t/nsmc/master/ratings_test.txt",
}


def _fetch_rows(url: str) -> list[tuple[str, str]]:
    """TSV(id\tdocument\tlabel)를 (document, label) 리스트로 파싱."""
    resp = httpx.get(url, timeout=30.0)
    resp.raise_for_status()
    lines = resp.text.splitlines()[1:]  # 헤더 스킵
    rows: list[tuple[str, str]] = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        _id, document, label = parts
        document = document.strip()
        if len(document) < _MIN_CHARS or label not in _LABEL_TEXT:
            continue
        rows.append((document, label))
    return rows


def _balanced_sample(
    rows: list[tuple[str, str]], per_label: int, rng: random.Random
) -> list[tuple[str, str]]:
    by_label: dict[str, list[str]] = {"0": [], "1": []}
    for document, label in rows:
        by_label[label].append(document)
    sample: list[tuple[str, str]] = []
    for label, documents in by_label.items():
        rng.shuffle(documents)
        for document in documents[:per_label]:
            sample.append((document, label))
    rng.shuffle(sample)
    return sample


def _write_jsonl(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for document, label in rows:
            record = {"instruction": _INSTRUCTION, "input": document, "output": _LABEL_TEXT[label]}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    rng = random.Random(_SEED)

    print("[prepare] NSMC train 원본 다운로드...")
    train_rows = _fetch_rows(_SOURCES["train"])
    print(f"[prepare] train 원본 {len(train_rows)}건 (필터 후)")

    print("[prepare] NSMC test 원본 다운로드...")
    test_rows = _fetch_rows(_SOURCES["test"])
    print(f"[prepare] test 원본 {len(test_rows)}건 (필터 후) -> val로 사용")

    train_sample = _balanced_sample(train_rows, _PER_LABEL_TRAIN, rng)
    val_sample = _balanced_sample(test_rows, _PER_LABEL_VAL, rng)

    _write_jsonl(_OUT_ROOT / "train.jsonl", train_sample)
    _write_jsonl(_OUT_ROOT / "val.jsonl", val_sample)

    train_pos = sum(1 for _, label in train_sample if label == "1")
    val_pos = sum(1 for _, label in val_sample if label == "1")
    print(
        f"\n[prepare] train: {len(train_sample)}건 (긍정 {train_pos} / 부정 {len(train_sample) - train_pos})"
    )
    print(
        f"[prepare] val:   {len(val_sample)}건 (긍정 {val_pos} / 부정 {len(val_sample) - val_pos})"
    )
    print(f"[prepare] 완료 — 저장 위치: {_OUT_ROOT}")


if __name__ == "__main__":
    main()
