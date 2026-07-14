# Mova v2/v3 스키마 마이그레이션 — 진행 상황 인계 문서

> 2026-07-13~14 세션에 걸쳐 진행. ORM/코드 레벨 작업(B~D, G)은 완료됨.
> **남은 작업은 아래 "미완료: E — 실제 마이그레이션 생성·적용" 하나뿐이다.**

## 확정된 결정 (재질문 금지)

| 항목 | 결정 |
|---|---|
| 진행 방식 | 기존 v1 테이블 **DROP 후 v2/v3로 재생성** (데이터 0건이라 안전) |
| create_all() | mova/viewer `create_all()` 호출 제거 완료 — Alembic이 전담 |
| embedding 차원 | **768** (Gemini `text-embedding-004`) |
| characters 1인 다역 | **허용** — `uq_characters_movie_actor_name` |
| tags (tag_kind,slug) UNIQUE | **적용 안 함** — 영화당 1행 조인 테이블 특성상 전역 UNIQUE 걸면 여러 영화가 같은 장르를 못 씀 (의도적 보류, `MOVA_ERD.md`의 `uq_tags_kind_slug` 서술은 정정 필요) |
| reviews ↔ user_actions | 분리 완료 — `reviews`(rating/body, `uq_reviews_user_movie`) / `user_actions`(action_type/action_at, UNIQUE 없음) |

## 완료됨 (2026-07-14)

ORM 전체(14개 테이블 + `watchlist`), `alembic/env.py` target_metadata 등록, `grid_oracle_database_manager.py` create_all 제거, `MOVA_ERD.md` watchlist 문서화. `ruff` 통과, `pytest apps/mova/tests` 18 pass(기존부터 깨져있던 2 fail은 무관·미수정).

## 미완료: E — 실제 마이그레이션 생성·적용

- 로컬: Docker Desktop WSL 통합이 꺼져 있어 DB 컨테이너 기동 불가 (사용자가 Docker Desktop에서 WSL 통합 켜야 함)
- SSH 서버(`ssh.suvisdev.cloud`): 2026-07-14 확인 시 `docker ps` 결과 컨테이너 0개 — DB 컨테이너 재기동 필요
- 순서: DB 컨테이너 기동 → `alembic revision --autogenerate -m "mova v2 schema"` → diff 사람이 검토 → `alembic upgrade head` → 롤백 검증(`downgrade -1` → 재적용)
- 기존 v1 테이블은 전부 0 rows 확인됨 (안전) — DROP 후 재생성해도 데이터 유실 없음

## 남은 잡일

- `apps/mova/_docs/mova_database.md`(untracked, SSH 서버 세션이 만든 것으로 추정)와 `MOVA_ERD.md` 내용이 겹치거나 다를 수 있음 — 비교·정리 필요
