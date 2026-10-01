"""06(Sentinel) H2 Phase B — 포스터 도메인 MVTec 형식 이상탐지 데이터셋 준비.

apps/ontology/resources/genre_classifier_train/{train,val}/<장르>/*.jpg 232장을
장르 구분 없이 풀어서 "정상 포스터"로 취급하고, MVTec AD 형식(train/good,
test/good+defect_*)으로 재구성한다. 이상 샘플은 실제 결함 포스터가 없으므로
합성 손상(블러/검은막/워터마크)으로 만든다 — PatchCore는 unsupervised라 이상
샘플 수가 적어도 되고(H2 가이드), 정상만 있으면 학습이 된다.

Usage (suvisdev 폴더에서):
  python scripts/prepare_sentinel_poster_dataset.py
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_SRC = Path("apps/ontology/resources/genre_classifier_train")
_OUT = Path("apps/ontology/resources/sentinel_poster")
_SEED = 42
_N_TEST_GOOD = 42  # 나머지는 train/good
_N_PER_DEFECT = 25  # test/good 풀에서 뽑아 손상시킴(defect 유형당)


def _blur(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=10))


def _black_bar(img: Image.Image) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    top = int(h * 0.35)
    bottom = int(h * 0.55)
    draw.rectangle([0, top, w, bottom], fill=(0, 0, 0))
    return out


def _watermark(img: Image.Image) -> Image.Image:
    out = img.convert("RGB").copy()
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    w, h = out.size
    text = "SAMPLE"
    for y in range(0, h, 80):
        for x in range(0, w, 160):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 110))
    return Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")


_DEFECTS = {"blur": _blur, "black_bar": _black_bar, "watermark": _watermark}


def main() -> None:
    all_images = sorted(_SRC.glob("*/*/*.jpg"))
    assert len(all_images) == 232, (
        f"예상 232장, 실제 {len(all_images)}장 — genre_classifier_train 구조 변경됨?"
    )

    rng = random.Random(_SEED)
    shuffled = all_images[:]
    rng.shuffle(shuffled)

    test_good_pool = shuffled[:_N_TEST_GOOD]
    train_good = shuffled[_N_TEST_GOOD:]

    train_good_dir = _OUT / "train" / "good"
    test_good_dir = _OUT / "test" / "good"
    train_good_dir.mkdir(parents=True, exist_ok=True)
    test_good_dir.mkdir(parents=True, exist_ok=True)

    for i, path in enumerate(train_good):
        Image.open(path).convert("RGB").save(train_good_dir / f"{i:04d}.jpg")

    for i, path in enumerate(test_good_pool):
        Image.open(path).convert("RGB").save(test_good_dir / f"{i:04d}.jpg")

    for defect_name, fn in _DEFECTS.items():
        defect_dir = _OUT / "test" / defect_name
        defect_dir.mkdir(parents=True, exist_ok=True)
        sample = rng.sample(test_good_pool, _N_PER_DEFECT)
        for i, path in enumerate(sample):
            img = Image.open(path).convert("RGB")
            fn(img).save(defect_dir / f"{i:04d}.jpg")

    print(f"train/good: {len(train_good)}")
    print(f"test/good: {len(test_good_pool)}")
    for defect_name in _DEFECTS:
        n = len(list((_OUT / "test" / defect_name).glob("*.jpg")))
        print(f"test/{defect_name}: {n}")


if __name__ == "__main__":
    main()
