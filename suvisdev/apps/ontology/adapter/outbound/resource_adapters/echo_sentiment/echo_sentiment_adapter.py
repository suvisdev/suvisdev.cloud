from __future__ import annotations

import logging
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult
from ontology.app.ports.output.sentiment_analysis_port import SentimentAnalysisPort

_BASE_MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
# HF repo가 이후 커밋에서 transformers v5 전용 코드로 바뀌어(RopeParameters 등)
# 이 프로젝트가 고정한 transformers==4.47.1과 안 맞게 됐다(H1/H4에서 확인,
# 07_sentiment_analysis_agent.md "5. H1 완료 기록" 참고). v5 마이그레이션
# 이전 커밋으로 고정해서 별도 몽키패치 없이 그대로 로드되게 한다.
_BASE_MODEL_REVISION = "e949c91dec92095908d34e6b560af77dd0c993f8"
_INSTRUCTION = "다음 영화 리뷰의 감정을 분석해줘."
_LABELS = ("긍정", "부정")

logger = logging.getLogger(__name__)


class EchoSentimentAdapter(SentimentAnalysisPort):
    """EXAONE-3.5-2.4B-Instruct(4bit) + Echo LoRA 어댑터로 감정을 분석한다.

    H1 VRAM 예산 판정에 따라 analyze() 호출마다 베이스 모델+어댑터를 새로
    올리고 끝나면 즉시 해제한다(TimmConvnextAdapter와 동일 전략) — mova
    채팅용 lora_server가 상시 VRAM을 점유하고 있어 Echo까지 상주시키면 8GB
    예산이 부족하다. 호출당 로드 비용(수십 초)이 있으나 실시간 채팅이 아닌
    보조 에이전트 호출 용도라 감수한다. 다건 백필은 analyze_batch()로 로드
    1회에 순회한다 — 상주가 아니라 배치 동안만 점유하므로 예산 판정과
    충돌하지 않는다.
    """

    def __init__(self, adapter_dir: Path, *, device: str | None = None) -> None:
        self._adapter_dir = adapter_dir
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    def analyze(self, text: str) -> SentimentResult:
        model, base_model, tokenizer = self._load()
        try:
            return self._infer(model, tokenizer, text)
        finally:
            del model, base_model
            self._release()

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult | None]:
        """모델을 한 번만 올려 texts를 순회 — CLI 백필용(건당 로드 시 41건 ≈ 30분).

        개별 추론 실패는 None으로 남기고 계속 진행한다(한 건이 배치를 죽이지
        않게). 반환 순서는 texts와 같다.
        """
        model, base_model, tokenizer = self._load()
        try:
            results: list[SentimentResult | None] = []
            for text in texts:
                try:
                    results.append(self._infer(model, tokenizer, text))
                except Exception as e:
                    logger.info("[echo_sentiment] 개별 추론 실패 err=%s", e)
                    results.append(None)
            return results
        finally:
            del model, base_model
            self._release()

    def _load(self) -> tuple[PeftModel, AutoModelForCausalLM, AutoTokenizer]:
        tokenizer = AutoTokenizer.from_pretrained(
            _BASE_MODEL_ID, revision=_BASE_MODEL_REVISION, trust_remote_code=True
        )

        if self._device == "cuda":
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            base_model = AutoModelForCausalLM.from_pretrained(
                _BASE_MODEL_ID,
                revision=_BASE_MODEL_REVISION,
                quantization_config=bnb_config,
                device_map={"": 0},
                trust_remote_code=True,
            )
        else:
            # 백엔드 파드(k3s)는 GPU가 없다. bitsandbytes 4bit는 CUDA 전용이라 CPU에서
            # transformers의 백엔드 검증이 `'frozenset' object has no attribute 'discard'`로
            # 죽어 09-27까지 감성 배치가 전량 실패했다(WORK_LOG_MOVA 09-27). CPU에선
            # 양자화 없이 bf16으로 올린다(2.4B ≈ 4.8GB, 16코어 forward 1회 수 초).
            base_model = AutoModelForCausalLM.from_pretrained(
                _BASE_MODEL_ID,
                revision=_BASE_MODEL_REVISION,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            ).to(self._device)
        model = PeftModel.from_pretrained(base_model, self._adapter_dir)
        model.eval()
        return model, base_model, tokenizer

    def _release(self) -> None:
        if self._device == "cuda":
            torch.cuda.empty_cache()

    def _infer(self, model: PeftModel, tokenizer: AutoTokenizer, text: str) -> SentimentResult:
        messages = [{"role": "user", "content": f"{_INSTRUCTION}\n\n{text}"}]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(self._device)

        label_token_ids = [
            tokenizer(label, add_special_tokens=False)["input_ids"][0] for label in _LABELS
        ]

        with torch.no_grad():
            logits = model(**inputs).logits[0, -1]
        label_logits = logits[label_token_ids]
        probs = torch.softmax(label_logits, dim=0)
        best = int(torch.argmax(probs))

        del inputs, logits
        return SentimentResult(label=_LABELS[best], score=float(probs[best]))
