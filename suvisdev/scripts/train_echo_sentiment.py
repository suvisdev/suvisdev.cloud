"""Echo(감성 분석 에이전트, 07_sentiment_analysis_agent.md) H3 — QLoRA 파인튜닝.

EXAONE-3.5-2.4B-Instruct를 4bit(nf4)로 로드하고 LoRA(r=8, q_proj/v_proj)를
붙여 NSMC 기반 감정 분류(긍정/부정) instruction-tuning 데이터로 학습한다.
데이터: apps/ontology/resources/echo_sentiment_train/{train,val}.jsonl
       (scripts/prepare_echo_sentiment_dataset.py 산출물, H2 완료)

EXAONE의 trust_remote_code custom modeling(`modeling_exaone.py`)이 실제
transformers.masking_utils.create_causal_mask 시그니처와 어긋나 있어(H1에서
확인, 07_sentiment_analysis_agent.md "5. H1 완료 기록" 참고) 이 스크립트도
동일한 compat 몽키패치를 로드 전에 적용한다.

학습은 수동 루프로 작성(TRL SFTTrainer 미사용) — trl까지 pinning하면
transformers/peft/trl 세 개의 버전 호환을 동시에 맞춰야 해서 리스크가 커지고,
이 태스크(출력이 "긍정"/"부정" 단 2가지) 자체가 단순해 수동 루프로 충분하다.

Usage (suvisdev 폴더에서, GPU 필요 — 실행 전 lora-server 등 다른 GPU
프로세스를 내려서 VRAM을 확보할 것: `systemctl --user stop lora-server`):
  python scripts/train_echo_sentiment.py
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
DATA_DIR = (
    Path(__file__).resolve().parents[1] / "apps" / "ontology" / "resources" / "echo_sentiment_train"
)
OUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "ontology"
    / "runs"
    / "echo_sentiment"
    / "adapter"
)

MAX_SEQ_LENGTH = 256  # H2 실측: p95=93, max=135 — 여유 있게 수용
BATCH_SIZE = 4
GRAD_ACCUM = 4
EPOCHS = 2
LEARNING_RATE = 2e-4

print(
    "=== patching transformers.masking_utils.create_causal_mask (EXAONE remote code signature drift) ==="
)
import transformers.masking_utils as _masking_utils

_original_create_causal_mask = _masking_utils.create_causal_mask


def _compat_create_causal_mask(
    *,
    config,
    input_embeds=None,
    inputs_embeds=None,
    attention_mask=None,
    cache_position=None,
    past_key_values=None,
    position_ids=None,
    **_ignored,
):
    return _original_create_causal_mask(
        config=config,
        inputs_embeds=input_embeds if input_embeds is not None else inputs_embeds,
        attention_mask=attention_mask,
        past_key_values=past_key_values,
        position_ids=position_ids,
    )


_masking_utils.create_causal_mask = _compat_create_causal_mask


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


class SentimentSFTDataset(Dataset):
    """프롬프트 구간은 -100으로 마스킹하고, 응답("긍정"/"부정") 구간만 loss에 반영."""

    def __init__(self, records: list[dict], tokenizer):
        self.records = records
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict:
        record = self.records[idx]
        prompt_messages = [
            {"role": "user", "content": f"{record['instruction']}\n\n{record['input']}"}
        ]
        prompt_text = self.tokenizer.apply_chat_template(
            prompt_messages, tokenize=False, add_generation_prompt=True
        )
        full_messages = prompt_messages + [{"role": "assistant", "content": record["output"]}]
        full_text = self.tokenizer.apply_chat_template(full_messages, tokenize=False)

        prompt_ids = self.tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        full_ids = self.tokenizer(
            full_text, add_special_tokens=False, truncation=True, max_length=MAX_SEQ_LENGTH
        )["input_ids"]

        labels = list(full_ids)
        prompt_len = min(len(prompt_ids), len(full_ids))
        for i in range(prompt_len):
            labels[i] = -100

        return {"input_ids": full_ids, "labels": labels}


def collate(batch: list[dict], pad_token_id: int) -> dict[str, torch.Tensor]:
    max_len = max(len(x["input_ids"]) for x in batch)
    input_ids, attention_mask, labels = [], [], []
    for x in batch:
        pad_len = max_len - len(x["input_ids"])
        input_ids.append(x["input_ids"] + [pad_token_id] * pad_len)
        attention_mask.append([1] * len(x["input_ids"]) + [0] * pad_len)
        labels.append(x["labels"] + [-100] * pad_len)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def main() -> None:
    print("=== free VRAM before load ===")
    free, total = torch.cuda.mem_get_info()
    print(f"free={free / 1e9:.2f}GB / total={total / 1e9:.2f}GB")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    print("=== loading model (4bit nf4) ===")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=bnb_config, device_map={"": 0}, trust_remote_code=True
    )

    # H1에서 확인된 LGAI custom code 갭 — get/set_input_embeddings 위임
    model.transformer.get_input_embeddings = types.MethodType(
        lambda self: self.wte, model.transformer
    )
    model.transformer.set_input_embeddings = types.MethodType(
        lambda self, value: setattr(self, "wte", value), model.transformer
    )
    model.get_input_embeddings = types.MethodType(lambda self: self.transformer.wte, model)
    model.set_input_embeddings = types.MethodType(
        lambda self, value: setattr(self.transformer, "wte", value), model
    )

    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_records = load_jsonl(DATA_DIR / "train.jsonl")
    val_records = load_jsonl(DATA_DIR / "val.jsonl")
    train_ds = SentimentSFTDataset(train_records, tokenizer)
    train_loader = DataLoader(
        train_ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=lambda b: collate(b, tokenizer.pad_token_id),
    )

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=LEARNING_RATE)

    print(
        f"\n=== 학습 시작: epochs={EPOCHS} batch={BATCH_SIZE} grad_accum={GRAD_ACCUM} (effective={BATCH_SIZE * GRAD_ACCUM}) ==="
    )
    model.train()
    step = 0
    for epoch in range(EPOCHS):
        epoch_loss = 0.0
        n_batches = 0
        optimizer.zero_grad()
        for i, batch in enumerate(train_loader):
            batch = {k: v.to("cuda") for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss / GRAD_ACCUM
            loss.backward()
            epoch_loss += outputs.loss.item()
            n_batches += 1

            if (i + 1) % GRAD_ACCUM == 0:
                torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
                optimizer.step()
                optimizer.zero_grad()
                step += 1
                if step % 20 == 0:
                    print(f"  epoch={epoch + 1} step={step} loss={outputs.loss.item():.4f}")

        print(f"=== epoch {epoch + 1} 완료 — mean loss={epoch_loss / n_batches:.4f} ===")

    peak_mem = torch.cuda.max_memory_allocated() / 1e6
    print(f"\n=== 학습 중 최대 VRAM 할당: {peak_mem:.1f} MB ===")

    print("\n=== val 정확도 평가 (생성 기반) ===")
    model.eval()
    model.config.use_cache = True
    correct = 0
    tp = fp = fn = 0  # 긍정 기준
    with torch.no_grad():
        for record in val_records:
            prompt_messages = [
                {"role": "user", "content": f"{record['instruction']}\n\n{record['input']}"}
            ]
            prompt_text = tokenizer.apply_chat_template(
                prompt_messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(prompt_text, return_tensors="pt", add_special_tokens=False).to(
                "cuda"
            )
            gen = model.generate(
                **inputs, max_new_tokens=5, do_sample=False, pad_token_id=tokenizer.pad_token_id
            )
            pred_text = tokenizer.decode(
                gen[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
            ).strip()
            pred = "긍정" if "긍정" in pred_text else ("부정" if "부정" in pred_text else "?")
            gold = record["output"]
            if pred == gold:
                correct += 1
            if pred == "긍정" and gold == "긍정":
                tp += 1
            elif pred == "긍정" and gold == "부정":
                fp += 1
            elif pred == "부정" and gold == "긍정":
                fn += 1

    accuracy = correct / len(val_records)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    print(
        f"val accuracy={accuracy:.4f} ({correct}/{len(val_records)})  precision={precision:.4f} recall={recall:.4f} f1={f1:.4f}"
    )

    print(f"\n=== 어댑터 저장: {OUT_DIR} ===")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT_DIR)
    tokenizer.save_pretrained(OUT_DIR)

    print("\n=== H3 GATE 결과 ===")
    print(
        f"val accuracy={accuracy:.4f} f1={f1:.4f} peak_vram={peak_mem:.1f}MB adapter_dir={OUT_DIR}"
    )


if __name__ == "__main__":
    main()
