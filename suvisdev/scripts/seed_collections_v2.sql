-- mova 컬렉션 큐레이션 확장 v2 (2026-08-18, PROGRESS 8순위 부분 완결)
--
-- v1(`seed_collections.sql`, 2026-08-06)의 5개(놀란/90년대 로맨스/SF 클래식/
-- 가족/액션) 위에 감독 필모그래피 3개를 얹는다.
--
-- **주의**: 이 파일은 컬렉션 row INSERT만 담당한다. 영화 배정은 7순위 완결
-- (PR #131)의 정식 CLI로 진행:
--
--   docker compose exec -T backend \
--     python scripts/assign_collection_cli.py --slug spielberg-world \
--     --movie-ids 232,386,576,521,717,901,580,1147,339,808,2,883 \
--     >> ~/assign_collection.log 2>&1
--
-- 이번 사이클 제외: D(korean-cinema), E(animation-masters), F(horror-classics).
-- rating DESC 기반 선정 시 성인물·노이즈 로우(rating=5.0, 소수 평가)에 오염
-- 확인. KR 성인 잔여 purge(2026-08-14 130편 purge 연장선) 선행 후 다음
-- 사이클에서 재시도.
--
-- 재실행 시 collections는 ON CONFLICT DO NOTHING이라 중복 안 생김. 배정은
-- assign_collection_cli.py가 UPDATE라 idempotent(이미 이 컬렉션 소속이면
-- no-op에 가까움).

INSERT INTO collections (slug, name, description, created_at, updated_at) VALUES
  ('spielberg-world', '스티븐 스필버그의 세계',
   '블록버스터와 인간 드라마를 오가는 스필버그 감독의 대표작들 — 쉰들러부터 인디아나 존스까지 한자리에.',
   now(), now()),
  ('tarantino-universe', '타란티노 유니버스',
   '펄프 픽션·킬 빌·바스터즈까지, 하나의 세계관으로 연결되는 쿠엔틴 타란티노의 필모그래피 전량.',
   now(), now()),
  ('ridley-scott-selects', '리들리 스콧 걸작선',
   '글래디에이터·블레이드 러너·마션 — 장르를 넘나드는 리들리 스콧의 정수를 골랐습니다.',
   now(), now())
ON CONFLICT (slug) DO NOTHING;
