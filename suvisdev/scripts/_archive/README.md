# scripts/_archive — 적용 완료된 일회성 스크립트 보관소

2026-09-11 코드 리뷰(⑤ 정리)에서 이동. 전부 **이미 적용이 끝난** 스키마
변경·리팩터링·데이터 시드 스크립트이며, 현행 스키마의 SSOT는 **alembic
체인**이다(`alembic history`).

- `add_*` / `rename_*` / `merge_*` / `migrate_*` / `apply_table_rename` /
  `drop_groups_tables`: 과거 수기 DDL. **재실행 금지** — 일부는 이후 rename으로
  방향이 되돌려져 현재 스키마와 충돌한다(예: `merge_reviews_into_interactions`).
- `seed_collections.sql`·`_v2.sql`: 구버전 시드(최종본은 v3 계열).
- `extract_kofic.py`·`extract_adapters.py`: Windows Cursor 트랜스크립트 경로
  하드코딩 일회성 복구 스크립트 — 이 저장소(WSL)에선 실행 자체가 불가.
- `run_db_maintenance_20260902.sh`: 2026-09-02 단발 정비 기록.

참조가 필요한 문서(`apps/mova/_docs/MOVA_ERD.md` 등)의 역사 서술은 이 폴더를
가리키는 것으로 읽으면 된다.
