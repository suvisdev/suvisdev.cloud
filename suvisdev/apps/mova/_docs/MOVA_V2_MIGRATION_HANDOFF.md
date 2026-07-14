# Mova v2/v3 스키마 마이그레이션 — 진행 상황 인계 문서

> 2026-07-13~14 세션에 걸쳐 진행. **전체 완료.** SSH 프로덕션 서버(`ssh.suvisdev.cloud`)에
> `alembic upgrade head`까지 적용 완료(리비전 `41f584bfcb4e`), 롤백 검증·컨테이너 재시작 후
> 데이터 유지까지 확인함. 남은 건 "남은 잡일" 하나뿐.

## 확정된 결정 (참고용, 이미 적용됨)

| 항목 | 결정 |
|---|---|
| embedding 차원 | **768** (Gemini `text-embedding-004`) |
| characters 1인 다역 | **허용** — `uq_characters_movie_actor_name` |
| tags (tag_kind,slug) UNIQUE | **적용 안 함** — 영화당 1행 조인 테이블 특성상 전역 UNIQUE 걸면 여러 영화가 같은 장르를 못 씀 (의도적 보류, `MOVA_ERD.md`의 `uq_tags_kind_slug` 서술은 정정 필요) |
| reviews ↔ user_actions | 분리 완료 — `reviews`(rating/body, `uq_reviews_user_movie`) / `user_actions`(action_type/action_at, UNIQUE 없음) |

## 완료됨 (2026-07-14)

- ORM 전체(14개 테이블 + `watchlist`), `alembic/env.py` target_metadata 등록, `grid_oracle_database_manager.py` create_all 제거, `MOVA_ERD.md` watchlist 문서화
- `alembic/env.py`에 `grid_neo_theone_base.Base`(titanic_passengers/bookings, dispatch_adress/inbox, vision_uploads) 등록 — 기존에 빠져있던 걸 발견해서 같이 고침. 이게 없으면 mova 마이그레이션 autogenerate가 저 테이블들을 "삭제 대상"으로 잘못 잡음
- 리비전 `41f584bfcb4e_mova_v2_schema.py` 생성 → autogenerate가 같이 잡아온 titanic_bookings(person_id→passenger_id) 변경은 무관한 diff라 수동으로 제거하고 mova/viewer 변경분만 남김
- SSH 서버에 적용 완료: `alembic upgrade head` → `downgrade -1`(롤백 확인) → `upgrade head`(재적용) → `docker compose restart db` 후 테이블 유지 확인
- `ruff` 통과, `pytest apps/mova/tests` 18 pass(기존부터 깨져있던 2 fail은 무관·미수정)
- 커밋: `0a6be07`(ORM 전체), `e535eda`(env.py Base 등록 수정), `2e9ea9b`(리비전 파일) — 전부 push·서버 pull 완료

## 남은 잡일

- `apps/mova/_docs/mova_database.md`(untracked, SSH 서버 세션이 만든 것으로 추정)와 `MOVA_ERD.md` 내용이 겹치거나 다를 수 있음 — 비교·정리 필요
- `titanic_persons` 테이블이 DB에 여전히 남아있음 — 현재 ORM 어디에도 대응 안 됨(진짜 레거시로 보임). 이번 마이그레이션 범위 밖이라 손대지 않음, 별도로 삭제할지 판단 필요
- 서버의 `.venv-alembic`(alembic 실행용, sudo 없이 uv로 만듦)은 재사용 가능하니 다음에 또 마이그레이션할 때 지우지 말 것
