from __future__ import annotations

import logging

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from dispatch.app.ports.output.moderation_port import ModerationPort

logger = logging.getLogger(__name__)

# smilegate-ai/kor_unsmile — KcELECTRA-base 위에 혐오표현·욕설을 실제로 파인튜닝한
# 멀티라벨 분류기. KcELECTRA-base 자체는 분류 헤드가 없어 임베딩 유사도로는
# 정상/비속어를 구분하지 못함이 실측으로 확인되어 이 모델로 교체했다.
_MODEL_NAME = "smilegate-ai/kor_unsmile"
_CLEAN_LABEL = "clean"
_CLEAN_THRESHOLD = 0.5

_tokenizer: AutoTokenizer | None = None
_model: AutoModelForSequenceClassification | None = None


def _load() -> tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        logger.info("[KorUnsmileModerationAdapter] %s 로딩 중...", _MODEL_NAME)
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        _model.eval()
        logger.info("[KorUnsmileModerationAdapter] 로딩 완료 | labels=%s", _model.config.id2label)
    return _tokenizer, _model


class KorUnsmileModerationAdapter(ModerationPort):
    def is_clean(self, text: str) -> bool:
        if not text.strip():
            return True
        tokenizer, model = _load()
        inputs = tokenizer(text, truncation=True, max_length=256, return_tensors="pt")
        with torch.no_grad():
            logits = model(**inputs).logits
        scores = torch.sigmoid(logits)[0]
        id2label = model.config.id2label
        clean_idx = next(i for i, label in id2label.items() if label.lower() == _CLEAN_LABEL)
        return scores[clean_idx].item() >= _CLEAN_THRESHOLD
