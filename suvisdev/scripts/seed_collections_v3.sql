-- mova 컬렉션 큐레이션 확장 v3 (2026-09-01, PROGRESS 8순위 완결 사이클)
--
-- v2(2026-08-18)에서 KR 성인·노이즈 오염으로 이월했던 D/E/F 3개.
-- 선행 조건이던 KR 성인 잔여 purge v2(2026-09-01, 9편 삭제) 완료 후 진행.
-- 후보 선정: rating 단독이 아니라 picks 인터랙션 존재 + 수동 검수로
-- rating=5.0 소수평가 노이즈(만선·흥부와 놀부 등)와 미개봉 신작을 배제.
--
-- **주의**: 이 파일은 컬렉션 row INSERT만 담당한다. 영화 배정은 정식 CLI로:
--
--   docker compose exec -T backend \
--     python scripts/assign_collection_cli.py --slug korean-cinema \
--     --movie-ids 147,925,565,2128,2095,2261,2063,1638,2489,2910
--   docker compose exec -T backend \
--     python scripts/assign_collection_cli.py --slug animation-masters \
--     --movie-ids 330,150,354,834,298,210
--   docker compose exec -T backend \
--     python scripts/assign_collection_cli.py --slug horror-classics \
--     --movie-ids 464,243,426,620,4494,2064
--
-- 재실행 시 collections는 ON CONFLICT DO NOTHING이라 중복 안 생김.

INSERT INTO collections (slug, name, description, created_at, updated_at) VALUES
  ('korean-cinema', '한국 영화의 힘',
   '기생충·살인의 추억·아가씨 — 세계가 주목한 한국 영화의 대표작들을 한자리에 모았습니다.',
   now(), now()),
  ('animation-masters', '애니메이션 걸작선',
   '주토피아부터 너의 이름은.까지 — 세대를 가리지 않고 사랑받는 애니메이션 명작 모음.',
   now(), now()),
  ('horror-classics', '호러 클래식',
   '싸이코·샤이닝·엑소시스트 — 공포 영화의 문법을 만든 고전들과 한국 호러의 대표작.',
   now(), now())
ON CONFLICT (slug) DO NOTHING;
