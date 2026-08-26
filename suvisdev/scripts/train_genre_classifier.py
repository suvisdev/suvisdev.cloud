"""ConvNeXt-Nano 포스터→장르 분류기 파인튜닝(H2).

apps/ontology/resources/genre_classifier_train/{train,val}/<장르>/*.jpg를
ImageFolder로 읽어 ConvNeXt-Nano(pretrained)의 backbone은 얼리고 head(분류
레이어)만 학습한다. 클래스당 표본이 14~66장으로 적어(<100장) 문서 기준
"소량" 전략을 따른다.

가중치/클래스 매핑 산출물:
  apps/ontology/runs/genre_classify/weights/best.pth
  apps/ontology/runs/genre_classify/classes.json

Usage (suvisdev 폴더에서):
  python scripts/train_genre_classifier.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for p in (_BACKEND, _APPS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

_DATA_ROOT = _APPS / "ontology" / "resources" / "genre_classifier_train"
_RUNS_DIR = _APPS / "ontology" / "runs" / "genre_classify"
_WEIGHTS_PATH = _RUNS_DIR / "weights" / "best.pth"
_CLASSES_PATH = _RUNS_DIR / "classes.json"

_SEED = 42
_EPOCHS = 20
_BATCH_SIZE = 16
_LR = 1e-3
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _build_model_and_transforms(num_classes: int):
    import timm
    from timm.data import create_transform, resolve_data_config

    model = timm.create_model("convnext_nano", pretrained=True, num_classes=num_classes)

    # backbone freeze, head(NormMlpClassifierHead: norm+fc)만 학습 —
    # 클래스당 표본이 적어(<100장) 전체 파인튜닝은 과적합 위험이 크다.
    for param in model.parameters():
        param.requires_grad = False
    for param in model.head.parameters():
        param.requires_grad = True

    data_cfg = resolve_data_config({}, model=model)
    train_tf = create_transform(**data_cfg, is_training=True)
    val_tf = create_transform(**data_cfg, is_training=False)
    return model, train_tf, val_tf


def _run_epoch(model, loader, optimizer, criterion, *, train: bool) -> tuple[float, float]:
    model.train(mode=train)
    total_loss = 0.0
    correct = 0
    total = 0
    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for images, labels in loader:
            images, labels = images.to(_DEVICE), labels.to(_DEVICE)
            if train:
                optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            if train:
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * images.size(0)
            correct += (outputs.argmax(dim=1) == labels).sum().item()
            total += images.size(0)
    return total_loss / total, correct / total


def main() -> None:
    torch.manual_seed(_SEED)

    train_ds_probe = ImageFolder(str(_DATA_ROOT / "train"))
    classes = train_ds_probe.classes
    num_classes = len(classes)
    print(f"[train] 클래스 {num_classes}개: {classes}")

    model, train_tf, val_tf = _build_model_and_transforms(num_classes)
    model = model.to(_DEVICE)
    print(f"[train] device={_DEVICE}")

    train_ds = ImageFolder(str(_DATA_ROOT / "train"), transform=train_tf)
    val_ds = ImageFolder(str(_DATA_ROOT / "val"), transform=val_tf)
    assert (
        train_ds.classes == classes and val_ds.classes == classes
    ), "train/val 클래스 목록이 다릅니다 — ImageFolder 폴더 구성을 확인하세요."

    train_loader = DataLoader(train_ds, batch_size=_BATCH_SIZE, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=_BATCH_SIZE, shuffle=False, num_workers=2)

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=_LR)
    criterion = nn.CrossEntropyLoss()

    _WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    best_val_acc = 0.0

    for epoch in range(1, _EPOCHS + 1):
        train_loss, train_acc = _run_epoch(model, train_loader, optimizer, criterion, train=True)
        val_loss, val_acc = _run_epoch(model, val_loader, optimizer, criterion, train=False)
        print(
            f"[train] epoch {epoch}/{_EPOCHS} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), _WEIGHTS_PATH)
            print(f"[train]   -> best 갱신, 저장: {_WEIGHTS_PATH}")

    _CLASSES_PATH.write_text(
        json.dumps({str(i): name for i, name in enumerate(classes)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[train] 완료 — best_val_acc={best_val_acc:.4f}")
    print(f"[train] weights: {_WEIGHTS_PATH}")
    print(f"[train] classes: {_CLASSES_PATH}")


if __name__ == "__main__":
    main()
