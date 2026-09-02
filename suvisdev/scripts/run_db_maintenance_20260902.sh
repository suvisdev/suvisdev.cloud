#!/usr/bin/env bash
# 2026-09-02 DB 정비 3종 — 분류기 차단으로 사용자 실행용(터널 15432 필요).
# ① 에디터 리뷰 41건 감정분석+자동별점+영화평점 재계산
# ② vote_count=0 신규 인입분 TMDB 백필(멱등)
# ③ TMDB 삭제 404 영화 id=2769(ARTMS: Icarus) 삭제 — 유저 데이터 0건 확인됨
set -euo pipefail
cd "$(dirname "$0")/.."

export MOVA_DATABASE_URL=$(grep -oP '^MOVA_DATABASE_URL=\K.*' .env)

echo "== ① 감정분석 백필(41건, 건당 모델 로드라 오래 걸림) =="
~/.pyenv/shims/python scripts/backfill_review_sentiment_cli.py

echo "== ② vote_count 백필(멱등) =="
~/.pyenv/shims/python scripts/backfill_vote_counts.py

echo "== ③ 404 영화 2769 삭제 + 사후 검증 =="
~/.pyenv/shims/python - <<'EOF'
import os, psycopg
url = os.environ["MOVA_DATABASE_URL"].replace("+psycopg", "")
with psycopg.connect(url) as conn, conn.cursor() as cur:
    cur.execute("DELETE FROM movies WHERE id=2769")
    print("deleted rows:", cur.rowcount)
    cur.execute("SELECT count(*) FROM reviews WHERE sentiment_label IS NULL")
    print("reviews_no_sentiment:", cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM reviews WHERE rating IS NULL")
    print("reviews_null_rating:", cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM movies WHERE vote_count=0 OR vote_count IS NULL")
    print("movies_vote0:", cur.fetchone()[0])
    conn.commit()
EOF

echo "== 완료 =="
