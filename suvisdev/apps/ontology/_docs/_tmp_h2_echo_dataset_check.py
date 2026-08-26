"""H2 데이터 검증용 임시 스크립트 — Echo(07_sentiment_analysis) NSMC 데이터셋.

Gate 통과 후 삭제 예정. 확인 항목:
1. train/val 라벨 분포 (스크립트 자체가 균형 샘플링하지만 재검증)
2. EXAONE-3.5-2.4B-Instruct 토크나이저로 실제 프롬프트 포맷 후 토큰 길이 분포
   -> H3 max_seq_length 결정 근거
3. 데이터 로더가 패딩된 배치를 정상 반환하는지 (H2 Gate 조건)
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import torch
from transformers import AutoTokenizer

MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
DATA_DIR = Path(__file__).resolve().parents[1] / "resources" / "echo_sentiment_train"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def format_prompt(tokenizer, record: dict) -> str:
    messages = [
        {"role": "user", "content": f"{record['instruction']}\n\n{record['input']}"},
        {"role": "assistant", "content": record["output"]},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False)


def main() -> None:
    print("=== 라벨 분포 재검증 ===")
    for split in ("train", "val"):
        rows = load_jsonl(DATA_DIR / f"{split}.jsonl")
        labels = [r["output"] for r in rows]
        pos = labels.count("긍정")
        neg = labels.count("부정")
        print(f"{split}: 총 {len(rows)}건 (긍정 {pos} / 부정 {neg})")
        assert pos == neg, f"{split} 라벨 불균형: 긍정 {pos} vs 부정 {neg}"

    print("\n=== 토크나이저 로드 ===")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

    print("\n=== 토큰 길이 분포 (train) ===")
    train_rows = load_jsonl(DATA_DIR / "train.jsonl")
    lengths = [
        len(tokenizer(format_prompt(tokenizer, r), add_special_tokens=False)["input_ids"])
        for r in train_rows
    ]
    lengths.sort()
    p50 = lengths[len(lengths) // 2]
    p95 = lengths[int(len(lengths) * 0.95)]
    print(
        f"min={lengths[0]} mean={statistics.mean(lengths):.1f} p50={p50} p95={p95} max={lengths[-1]}"
    )

    max_seq_length = 256
    over_budget = sum(1 for n in lengths if n > max_seq_length)
    print(
        f"max_seq_length={max_seq_length} 초과 샘플: {over_budget}/{len(lengths)} ({over_budget / len(lengths):.1%})"
    )

    print("\n=== 배치 반환 확인 (batch_size=4, padding) ===")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    batch_texts = [format_prompt(tokenizer, r) for r in train_rows[:4]]
    batch = tokenizer(
        batch_texts,
        padding=True,
        truncation=True,
        max_length=max_seq_length,
        return_tensors="pt",
    )
    print(f"input_ids shape: {batch['input_ids'].shape}")
    print(f"attention_mask shape: {batch['attention_mask'].shape}")
    assert batch["input_ids"].shape == batch["attention_mask"].shape
    assert isinstance(batch["input_ids"], torch.Tensor)

    print("\n=== 샘플 프롬프트 (1건) ===")
    print(format_prompt(tokenizer, train_rows[0]))

    print("\n=== H2 GATE PASS ===")


if __name__ == "__main__":
    main()
