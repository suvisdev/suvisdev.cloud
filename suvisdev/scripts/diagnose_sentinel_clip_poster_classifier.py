"""06(Sentinel) §6.5 방향 결정 검증 — "포스터 판별"을 CLIP 제로샷으로 바꿔도
되는지, 이미 만들어둔 라벨셋(test/good, test/non_poster_easy,
test/alt_poster_control)으로 학습 없이 바로 확인한다.

PatchCore(patch-level 텍스처 비교)가 "포스터냐 아니냐"라는 전역적·구성적
질문에 안 맞는다는 게 §6에서 확인됐다. CLIP은 이미지 전체를 텍스트 프롬프트와
대조하는 전역 임베딩 방식이라 이 질문에 구조적으로 더 맞을 것이라는 가설을
제로샷(파인튜닝 없이)으로 먼저 검증한다 — 맞으면 01(장르 분류)류 별도
학습 없이 바로 쓸 수 있다.

Usage (컨테이너 안 /suvisdev에서 — 최초 실행 시 CLIP 가중치 다운로드):
  python scripts/diagnose_sentinel_clip_poster_classifier.py
"""

from __future__ import annotations

import glob

import numpy as np
import torch
from PIL import Image
from sklearn.metrics import roc_auc_score
from transformers import CLIPModel, CLIPProcessor

_ROOT = "apps/ontology/resources/sentinel_poster/test"
_MODEL_NAME = "openai/clip-vit-base-patch32"

_POSTER_PROMPTS = [
    "a movie poster",
    "an official theatrical movie poster with the film title",
]
_NON_POSTER_PROMPTS = [
    "a photograph",
    "a still frame from a movie scene or a portrait photo of a person",
]


def _load_model() -> tuple[CLIPModel, CLIPProcessor, torch.device]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CLIPModel.from_pretrained(_MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(_MODEL_NAME)
    try:
        model = model.to(device).eval()
    except RuntimeError as e:
        print(f"  GPU 로드 실패({e}) — CPU로 대체")
        device = torch.device("cpu")
        model = model.to(device).eval()
    return model, processor, device


def _poster_probs(
    model: CLIPModel, processor: CLIPProcessor, device: torch.device, paths: list[str]
) -> np.ndarray:
    prompts = _POSTER_PROMPTS + _NON_POSTER_PROMPTS
    text_inputs = processor(text=prompts, return_tensors="pt", padding=True).to(device)
    with torch.no_grad():
        text_features = model.get_text_features(**text_inputs)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    probs = []
    batch_size = 16
    for i in range(0, len(paths), batch_size):
        batch_paths = paths[i : i + batch_size]
        images = [Image.open(p).convert("RGB") for p in batch_paths]
        image_inputs = processor(images=images, return_tensors="pt").to(device)
        with torch.no_grad():
            image_features = model.get_image_features(**image_inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            logits = 100.0 * image_features @ text_features.T
            sims = logits.softmax(dim=-1).cpu().numpy()
        # 프롬프트별 유사도를 poster/non-poster 그룹으로 모아 평균
        poster_sim = sims[:, : len(_POSTER_PROMPTS)].sum(axis=1)
        probs.extend(poster_sim.tolist())
    return np.array(probs)


def main() -> None:
    model, processor, device = _load_model()
    print(f"device={device}")

    groups = {
        "good": sorted(glob.glob(f"{_ROOT}/good/*.jpg")),
        "non_poster_easy": sorted(glob.glob(f"{_ROOT}/non_poster_easy/*.jpg")),
        "alt_poster_control": sorted(glob.glob(f"{_ROOT}/alt_poster_control/*.jpg")),
    }
    for name, paths in groups.items():
        print(f"{name}: n={len(paths)}")

    poster_prob = {
        name: _poster_probs(model, processor, device, paths) for name, paths in groups.items()
    }

    print("\n=== 그룹별 CLIP poster_prob(포스터일 확률, 제로샷) 분포 ===")
    for name, probs in poster_prob.items():
        print(
            f"{name:20s}: n={len(probs):3d} mean={probs.mean():.3f} std={probs.std():.3f} "
            f"min={probs.min():.3f} max={probs.max():.3f}"
        )

    print("\n=== 0.5 임계값 기준 정확도 ===")
    for name, probs in poster_prob.items():
        is_poster_label = name in ("good", "alt_poster_control")
        pred_poster = probs >= 0.5
        acc = (pred_poster == is_poster_label).mean() if is_poster_label else (~pred_poster).mean()
        print(f"{name:20s}: 정답률={acc * 100:.1f}%")

    print("\n=== AUROC(포스터=good+alt_poster_control vs 진짜 이상=non_poster_easy) ===")
    neg_score = np.concatenate([1 - poster_prob["good"], 1 - poster_prob["alt_poster_control"]])
    pos_score = 1 - poster_prob["non_poster_easy"]
    y = np.concatenate([np.zeros(len(neg_score)), np.ones(len(pos_score))])
    s = np.concatenate([neg_score, pos_score])
    print(f"AUROC = {roc_auc_score(y, s):.4f}  (anomaly score = 1 - poster_prob)")


if __name__ == "__main__":
    main()
