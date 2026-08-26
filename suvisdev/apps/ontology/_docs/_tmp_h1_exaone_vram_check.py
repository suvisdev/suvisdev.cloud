"""H1 VRAM 실측용 임시 스크립트 — EXAONE-3.5-2.4B-Instruct 4bit QLoRA 로드 체크.

Gate 통과 후 삭제 예정 (07_sentiment_analysis_agent.md H1).
"""

from __future__ import annotations

import types

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

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

print("=== free VRAM before load ===")
free, total = torch.cuda.mem_get_info()
print(f"free={free/1e9:.2f}GB / total={total/1e9:.2f}GB")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

print("=== loading tokenizer ===")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

print("=== loading model (4bit nf4) ===")
before = torch.cuda.memory_allocated()
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map={"": 0},
    trust_remote_code=True,
)
after_load = torch.cuda.memory_allocated()
print(f"4bit model load delta: {(after_load - before)/1e6:.1f} MB")

print("=== patching missing get/set_input_embeddings (LGAI custom code gap) ===")


def _get_input_embeddings(self):
    return self.wte


def _set_input_embeddings(self, value):
    self.wte = value


model.transformer.get_input_embeddings = types.MethodType(_get_input_embeddings, model.transformer)
model.transformer.set_input_embeddings = types.MethodType(_set_input_embeddings, model.transformer)
model.get_input_embeddings = types.MethodType(lambda self: self.transformer.wte, model)
model.set_input_embeddings = types.MethodType(
    lambda self, value: setattr(self.transformer, "wte", value), model
)

print("=== attaching LoRA ===")
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
after_lora = torch.cuda.memory_allocated()
print(f"LoRA attach delta: {(after_lora - after_load)/1e6:.1f} MB")

print("=== forward pass smoke test ===")
inputs = tokenizer("감정 분석 태스크 QLoRA 테스트입니다.", return_tensors="pt").to("cuda")
with torch.no_grad():
    out = model(**inputs)
print("logits shape:", out.logits.shape)

after_forward = torch.cuda.memory_allocated()
print(f"total allocated after forward: {after_forward/1e6:.1f} MB")

free_after, _ = torch.cuda.mem_get_info()
print(f"free VRAM after all: {free_after/1e9:.2f}GB")

print("=== DONE ===")
