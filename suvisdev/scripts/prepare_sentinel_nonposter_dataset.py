"""06(Sentinel) 범위 재정의 — "포스터가 아닌 이미지" negative 데이터셋 준비.

06_anomaly_detection_agent.md §5 재정의에 따라 이상(anomaly) = 포스터가 아닌
이미지로 바꾼다. TMDB에서 기존 genre_classifier_train(포스터 232장)과 같은
영화 풀의 tmdb id를 재사용해 두 난이도로 negative를 모은다.

- easy(진짜 이상): backdrop(예고편/필름 스틸, 16:9 가로) + cast profile(인물
  사진, 세로) — 구도·내용이 포스터와 명백히 다르다. `test/non_poster_easy`.
- alt_poster_control(위양성 대조군, **정상**): TMDB posters 배열 중 학습에
  쓰인 "대표 포스터"가 아닌 대체 포스터(textless 티저, 비주력 언어판)도
  전부 TMDB의 공식 포스터라서 harvester가 이걸 가져오는 건 수집 오류가
  아니다 — 이상으로 라벨링하면 모델이 "포스터 맞다"고 정확히 판단해도
  실패로 집계된다. 그래서 이상 라벨이 아니라 test/good과 점수 분포를
  비교하는 위양성 대조군으로 쓴다. `test/alt_poster_control`.
  **한계**: 진짜 hard negative(손상 다운로드, 플레이스홀더, 로고 등)는
  TMDB API에 없다 — harvester 실패 로그에서 수집하는 별도 과제로 남긴다.

**종횡비 누출 방지**: PatchCore 기본 전처리(Resize(256,256))는 종횡비를
무시하고 정사각형으로 찌그러뜨린다. 포스터는 2:3(가로:세로≈0.667)인데
backdrop(16:9≈1.78)을 그대로 넣으면 모델이 "많이 찌그러진 이미지=이상"이라는
내용과 무관한 지름길을 학습할 위험이 크다. 그래서 저장 전에 모든 negative를
2:3으로 center crop한다.

Usage (컨테이너 안 /suvisdev에서 — TMDB_API_KEY, 네트워크 필요):
  python scripts/prepare_sentinel_nonposter_dataset.py
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from random import Random

import httpx
from PIL import Image

_SRC_POSTER_ROOT = Path("apps/ontology/resources/genre_classifier_train")
_OUT = Path("apps/ontology/resources/sentinel_poster")
_SEED = 42
_TARGET_RATIO = 2 / 3  # 포스터 표준 종횡비(width/height)

_N_EASY_BACKDROP = 20
_N_EASY_CAST = 20
_N_HARD_TEXTLESS = 15
_N_HARD_ALTLANG = 15

_IMG_BASE = "https://image.tmdb.org/t/p"
_BACKDROP_SIZE = "w780"
_POSTER_SIZE = "w500"
_PROFILE_SIZE = "h632"

_DETAIL_URL = "https://api.themoviedb.org/3/movie/{id}"


def _center_crop_to_ratio(img: Image.Image, ratio: float) -> Image.Image:
    w, h = img.size
    current = w / h
    if current > ratio:  # 너무 가로로 김 -> 폭을 깎는다
        new_w = round(h * ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    if current < ratio:  # 너무 세로로 김 -> 높이를 깎는다
        new_h = round(w / ratio)
        top = (h - new_h) // 2
        return img.crop((0, top, w, top + new_h))
    return img


def _collect_tmdb_ids() -> list[int]:
    ids: set[int] = set()
    for path in _SRC_POSTER_ROOT.glob("*/*/tmdb-*.jpg"):
        m = re.search(r"tmdb-(\d+)\.jpg", path.name)
        if m:
            ids.add(int(m.group(1)))
    return sorted(ids)


def _fetch_movie(client: httpx.Client, tmdb_id: int, api_key: str) -> dict | None:
    try:
        resp = client.get(
            _DETAIL_URL.format(id=tmdb_id),
            params={
                "api_key": api_key,
                "language": "ko-KR",
                "append_to_response": "credits,images",
                "include_image_language": "null,en,ko,ja,zh,fr,de,es,it,ru",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"  tmdb-{tmdb_id}: 조회 실패 ({e})")
        return None


def _download(client: httpx.Client, size: str, path: str) -> Image.Image | None:
    url = f"{_IMG_BASE}/{size}{path}"
    try:
        resp = client.get(url, timeout=15.0)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  다운로드 실패 {url}: {e}")
        return None
    from io import BytesIO

    return Image.open(BytesIO(resp.content)).convert("RGB")


def _save(img: Image.Image, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cropped = _center_crop_to_ratio(img, _TARGET_RATIO)
    cropped.save(out_dir / name, quality=90)


def main() -> None:
    api_key = os.environ["TMDB_API_KEY"]
    tmdb_ids = _collect_tmdb_ids()
    print(f"[prepare] genre_classifier_train에서 tmdb id {len(tmdb_ids)}개 확보")

    rng = Random(_SEED)
    shuffled = tmdb_ids[:]
    rng.shuffle(shuffled)

    easy_dir = _OUT / "test" / "non_poster_easy"
    hard_dir = _OUT / "test" / "alt_poster_control"

    counts = {"backdrop": 0, "cast": 0, "textless": 0, "altlang": 0}

    with httpx.Client() as client:
        for tmdb_id in shuffled:
            if all(
                [
                    counts["backdrop"] >= _N_EASY_BACKDROP,
                    counts["cast"] >= _N_EASY_CAST,
                    counts["textless"] >= _N_HARD_TEXTLESS,
                    counts["altlang"] >= _N_HARD_ALTLANG,
                ]
            ):
                break

            detail = _fetch_movie(client, tmdb_id, api_key)
            time.sleep(0.05)
            if detail is None:
                continue

            images = detail.get("images") or {}
            primary_poster_path = detail.get("poster_path")

            if counts["backdrop"] < _N_EASY_BACKDROP:
                backdrops = images.get("backdrops") or []
                if backdrops:
                    img = _download(client, _BACKDROP_SIZE, backdrops[0]["file_path"])
                    if img is not None:
                        _save(img, easy_dir, f"backdrop_{counts['backdrop']:04d}.jpg")
                        counts["backdrop"] += 1

            if counts["cast"] < _N_EASY_CAST:
                cast = detail.get("credits", {}).get("cast") or []
                profile = next((c for c in cast if c.get("profile_path")), None)
                if profile:
                    img = _download(client, _PROFILE_SIZE, profile["profile_path"])
                    if img is not None:
                        _save(img, easy_dir, f"cast_{counts['cast']:04d}.jpg")
                        counts["cast"] += 1

            posters = images.get("posters") or []
            if counts["textless"] < _N_HARD_TEXTLESS:
                textless = next(
                    (
                        p
                        for p in posters
                        if p.get("iso_639_1") is None and p["file_path"] != primary_poster_path
                    ),
                    None,
                )
                if textless:
                    img = _download(client, _POSTER_SIZE, textless["file_path"])
                    if img is not None:
                        _save(img, hard_dir, f"textless_{counts['textless']:04d}.jpg")
                        counts["textless"] += 1

            if counts["altlang"] < _N_HARD_ALTLANG:
                altlang = next(
                    (
                        p
                        for p in posters
                        if p.get("iso_639_1") not in (None, "ko", "en")
                        and p["file_path"] != primary_poster_path
                    ),
                    None,
                )
                if altlang:
                    img = _download(client, _POSTER_SIZE, altlang["file_path"])
                    if img is not None:
                        _save(img, hard_dir, f"altlang_{counts['altlang']:04d}.jpg")
                        counts["altlang"] += 1

    print(f"\n[prepare] easy/backdrop: {counts['backdrop']}/{_N_EASY_BACKDROP}")
    print(f"[prepare] easy/cast    : {counts['cast']}/{_N_EASY_CAST}")
    print(f"[prepare] hard/textless: {counts['textless']}/{_N_HARD_TEXTLESS}")
    print(f"[prepare] hard/altlang : {counts['altlang']}/{_N_HARD_ALTLANG}")
    print(
        f"\n[prepare] 완료 — {easy_dir}: {counts['backdrop'] + counts['cast']}장, "
        f"{hard_dir}: {counts['textless'] + counts['altlang']}장"
    )


if __name__ == "__main__":
    main()
