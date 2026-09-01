"""mova 채팅 학습 데이터(export_chat_training_dataset.py 산출물)로 공용 LoRA 어댑터를
주기적으로 재학습한다.

QLoRA가 아니라 두 백엔드를 모두 지원한다 (MOVA_TRAIN_BACKEND 환경변수):
- "plain" (기본값): 양자화 안 된 fp16 모델(Qwen2.5-1.5B-Instruct)에 표준 LoRA.
  현재 GPU(8GB) 여유로는 이 경로만 안정적으로 돈다 — EXAONE-AWQ는 모델 로드만으로
  5.3GB+를 써서 OOM이 재현됨(_docs/EXAONE_LOCAL_AI_SETUP.md 7-2 참고).
- "awq_gptqmodel": AWQ 체크포인트(EXAONE 등) + gptqmodel + peft. VRAM 여유가
  생기면 MOVA_TRAIN_BACKEND=awq_gptqmodel, MOVA_TRAIN_BASE_MODEL을 AWQ 체크포인트
  경로로 바꾸기만 하면 된다 — 이미 이 경로로 학습 성공을 확인한 적 있음(loss
  10.06→7.52). gradient_checkpointing 필수, torch_awq.py no_grad 패치 필요.

학습된 어댑터는 ~/lora_adapters/mova_<timestamp>/에 저장되고, ~/lora_adapters/LATEST
파일이 그 경로를 가리키도록 갱신한다 — 서빙 쪽은 이 파일만 읽으면 최신 어댑터를 안다.

Usage (~/.venv-exaone 활성화 후, suvisdev 폴더에서):
  python scripts/train_mova_lora.py [--dataset PATH] [--epochs 3]
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

_BACKEND = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND.parent
_DEFAULT_DATASET = _BACKEND / "apps" / "mova" / "_docs" / "chat_training_dataset.jsonl"
_ADAPTERS_ROOT = Path(os.getenv("LORA_ADAPTERS_ROOT", str(Path.home() / "lora_adapters")))

_TRAIN_BACKEND = os.getenv("MOVA_TRAIN_BACKEND", "plain")
_BASE_MODEL_PATH = os.getenv("MOVA_TRAIN_BASE_MODEL", str(_REPO_ROOT / "Qwen2.5-1.5B-Instruct"))

_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def _load_base_model():
    if _TRAIN_BACKEND == "awq_gptqmodel":
        # gptqmodel은 transformers v5를 요구해 v4 환경에서는 임포트 자체가
        # 실패하므로 이 분기 안에서만 지연 임포트한다(설치도 이 분기 사용 시에만).
        import gptqmodel.nn_modules.qlinear.gemm_awq as _gemm_awq
        from gptqmodel import BACKEND, GPTQModel

        # peft==0.19.1이 gptqmodel의 최신 클래스명을 못 따라가는 업스트림 버그 우회.
        _gemm_awq.AwqGEMMQuantLinear = _gemm_awq.AwqGEMMLinear

        model = GPTQModel.load(
            _BASE_MODEL_PATH, device="cuda:0", trust_remote_code=True, backend=BACKEND.TORCH
        )
        return model.model
    return AutoModelForCausalLM.from_pretrained(
        _BASE_MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="cuda:0",
        trust_remote_code=True,
    )


def _load_dataset(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _build_example(tokenizer, prompt: str, completion: str) -> dict[str, torch.Tensor]:
    """prompt 부분은 label=-100으로 마스킹해 completion에 대해서만 loss를 계산한다."""
    # transformers 버전에 따라 apply_chat_template(return_tensors="pt")의 반환형이
    # 순수 텐서/BatchEncoding으로 갈리므로 return_dict=True를 명시해 통일한다.
    prompt_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )["input_ids"]
    full_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}, {"role": "assistant", "content": completion}],
        add_generation_prompt=False,
        return_tensors="pt",
        return_dict=True,
    )["input_ids"]
    prompt_len = prompt_ids.shape[1]
    labels = full_ids.clone()
    labels[:, :prompt_len] = -100
    return {"input_ids": full_ids, "labels": labels}


def main(dataset_path: Path, epochs: int) -> None:
    examples = _load_dataset(dataset_path)
    if not examples:
        print(f"[train] 학습 데이터가 없습니다: {dataset_path}")
        return
    print(f"[train] 백엔드={_TRAIN_BACKEND} 베이스={_BASE_MODEL_PATH} 데이터={len(examples)}건")

    tokenizer = AutoTokenizer.from_pretrained(_BASE_MODEL_PATH, trust_remote_code=True)
    base = _load_base_model()

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=_TARGET_MODULES,
        task_type="CAUSAL_LM",
    )
    peft_model = get_peft_model(base, lora_config)
    # 8GB VRAM에서는 fp16 2.4B(plain)도 긴 프롬프트 활성값으로 OOM이 나므로
    # 백엔드와 무관하게 gradient checkpointing을 켠다.
    base.enable_input_require_grads()
    peft_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    peft_model.print_trainable_parameters()
    peft_model.train()

    opt = torch.optim.AdamW([p for p in peft_model.parameters() if p.requires_grad], lr=1e-4)

    for epoch in range(epochs):
        epoch_loss = 0.0
        for i, ex in enumerate(examples):
            batch = _build_example(tokenizer, ex["prompt"], ex["completion"])
            input_ids = batch["input_ids"].to("cuda:0")
            labels = batch["labels"].to("cuda:0")

            kwargs = {"use_cache": False}  # gradient checkpointing과 호환(공통 적용)
            out = peft_model(input_ids=input_ids, labels=labels, **kwargs)
            out.loss.backward()
            opt.step()
            opt.zero_grad()
            epoch_loss += out.loss.item()
            print(
                f"[train] epoch={epoch} {i + 1}/{len(examples)} loss={out.loss.item():.4f}",
                flush=True,
            )
        print(f"[train] epoch={epoch} 평균 loss={epoch_loss / len(examples):.4f}")

    version = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_dir = _ADAPTERS_ROOT / f"mova_{version}"
    peft_model.save_pretrained(str(out_dir))

    latest_file = _ADAPTERS_ROOT / "LATEST"
    latest_file.write_text(f"{out_dir}\n{_TRAIN_BACKEND}\n{_BASE_MODEL_PATH}\n", encoding="utf-8")
    print(f"[train] 완료: {out_dir}")
    print(f"[train] LATEST 갱신: {latest_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()
    main(args.dataset, args.epochs)
