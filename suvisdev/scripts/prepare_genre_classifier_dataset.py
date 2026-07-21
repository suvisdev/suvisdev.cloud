"""MOVA 영화 포스터 → 장르 분류기 학습용 데이터셋 준비 1회 스크립트.

movies 테이블(slug/title/poster_url)을 읽어 TMDB에서 장르를 다시 조회(테이블에
genres 컬럼이 없어 재조회 필요)하고, 포스터 이미지를 내려받아
apps/ontology/resources/genre_classifier_train/{train,val}/<대분류>/*.jpg
형태의 ImageFolder 데이터셋으로 저장한다.

TMDB 세부 장르(19개)는 데이터가 적어 클래스당 표본이 너무 희박해지므로
6개 대분류로 묶는다(_GENRE_TO_BUCKET). 영화당 TMDB가 반환하는 첫 번째 장르를
대표 장르로 사용한다.

train/val은 대분류별로 80:20, seed=42로 고정 분할한다(클래스별 최소 1장은
val에 배정).

Usage (suvisdev 폴더에서):
  python scripts/prepare_genre_classifier_dataset.py
"""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for p in (_BACKEND, _APPS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

_OUT_ROOT = _APPS / "ontology" / "resources" / "genre_classifier_train"
_SEED = 42
_VAL_RATIO = 0.2

# TMDB 세부 장르(ko-KR) → 학습용 대분류 6종
_GENRE_TO_BUCKET = {
    "액션": "action", "모험": "action", "전쟁": "action", "서부": "action",
    "SF": "scifi_fantasy", "판타지": "scifi_fantasy",
    "공포": "horror_thriller", "스릴러": "horror_thriller",
    "미스터리": "horror_thriller", "범죄": "horror_thriller",
    "코미디": "comedy",
    "드라마": "drama_romance", "로맨스": "drama_romance",
    "역사": "drama_romance", "음악": "drama_romance", "다큐멘터리": "drama_romance",
    "애니메이션": "animation_family", "가족": "animation_family",
}


async def main() -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory, reload_env
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
    from sqlalchemy import text

    reload_env()
    keymaker = get_keymaker()
    catalog = TmdbCatalogAdapter(keymaker.tmdb_api_key)

    factory = get_mova_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT slug, title, poster_url FROM movies "
                    "WHERE poster_url IS NOT NULL AND poster_url != ''"
                )
            )
        ).all()

    print(f"[prepare] 포스터 보유 영화 {len(rows)}편 로드")

    buckets: dict[str, list[tuple[str, bytes]]] = {}
    skipped_no_genre = 0
    skipped_download = 0

    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, (slug, title, poster_url) in enumerate(rows, 1):
            try:
                snapshots = await catalog.search(title, page=1)
            except Exception as e:
                print(f"  [{i}/{len(rows)}] {title} - TMDB 검색 실패: {e}")
                skipped_no_genre += 1
                continue
            if not snapshots or not snapshots[0].genres:
                skipped_no_genre += 1
                continue
            primary_genre = snapshots[0].genres[0]
            bucket = _GENRE_TO_BUCKET.get(primary_genre)
            if bucket is None:
                skipped_no_genre += 1
                continue

            try:
                resp = await client.get(poster_url)
                resp.raise_for_status()
            except Exception as e:
                print(f"  [{i}/{len(rows)}] {title} - 포스터 다운로드 실패: {e}")
                skipped_download += 1
                continue

            buckets.setdefault(bucket, []).append((slug, resp.content))
            print(f"  [{i}/{len(rows)}] {title} -> {bucket} ({primary_genre})")

    print(f"[prepare] 장르 매칭 실패(스킵): {skipped_no_genre}편")
    print(f"[prepare] 포스터 다운로드 실패(스킵): {skipped_download}편")

    rng = random.Random(_SEED)
    total_train = 0
    total_val = 0
    print("\n[prepare] 클래스별 분포:")
    for bucket, items in sorted(buckets.items()):
        rng.shuffle(items)
        n_val = max(1, round(len(items) * _VAL_RATIO)) if len(items) > 1 else 0
        val_items = items[:n_val]
        train_items = items[n_val:]

        for split, split_items in (("train", train_items), ("val", val_items)):
            split_dir = _OUT_ROOT / split / bucket
            split_dir.mkdir(parents=True, exist_ok=True)
            for slug, content in split_items:
                (split_dir / f"{slug}.jpg").write_bytes(content)

        total_train += len(train_items)
        total_val += len(val_items)
        print(f"  {bucket}: train={len(train_items)} val={len(val_items)}")

    print(f"\n[prepare] 완료 — train={total_train} val={total_val} 저장 위치: {_OUT_ROOT}")


if __name__ == "__main__":
    asyncio.run(main())
