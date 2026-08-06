-- mova 컬렉션 시드 — 2026-08-06, 5개 큐레이션(놀란/90년대 로맨스/SF 클래식/가족/액션)
--
-- movies.collection_id는 단일 FK(한 영화 = 한 컬렉션)라, 겹치는 후보는
-- 우선순위(감독 기반 > 시대+장르 > 장르 단독)에 따라 상위 컬렉션에만 배정하고
-- 하위 컬렉션 후보 목록에서는 미리 제외했다(쿼리 단계에서 조사 완료, 실행
-- 시점엔 재확인 없이 그대로 배정).
--
-- 재실행 시 collections는 ON CONFLICT DO NOTHING이라 중복 안 생기지만,
-- 이미 다른 컬렉션에 배정된 영화가 있으면 UPDATE가 마지막 실행 기준으로
-- 덮어쓴다 — 재실행은 "처음 상태로 되돌리기" 용도로만 쓸 것.

INSERT INTO collections (slug, name, description, created_at, updated_at) VALUES
  ('nolan-world', '크리스토퍼 놀란의 세계',
   '시간과 기억, 꿈을 뒤트는 크리스토퍼 놀란의 필모그래피 전체를 한자리에 모았습니다.',
   now(), now()),
  ('90s-romance', '90년대 로맨스',
   'CD플레이어와 편지가 어울리던 시절, 가장 순수했던 사랑 이야기들.',
   now(), now()),
  ('sf-classics', 'SF 클래식',
   '장르의 문법을 새로 쓴 SF 걸작들 — 지금 봐도 낡지 않은 상상력.',
   now(), now()),
  ('family-picks', '가족과 함께',
   '온 가족이 함께 웃고 울 수 있는, 세대를 넘어 사랑받는 애니메이션과 가족 영화.',
   now(), now()),
  ('action-essentials', '액션의 정수',
   '군더더기 없는 긴장감과 손에 땀을 쥐게 하는 액션의 진수만 골랐습니다.',
   now(), now())
ON CONFLICT (slug) DO NOTHING;

-- 1. 크리스토퍼 놀란의 세계 — movie_directors 기준 놀란 감독 전 필모그래피(12편)
UPDATE movies SET collection_id = (SELECT id FROM collections WHERE slug = 'nolan-world')
WHERE id IN (99, 106, 85, 375, 229, 1, 113, 280, 221, 725, 478, 1531);

-- 2. 90년대 로맨스 — release_year 1990~1999 + 로맨스 태그, 평점순 top 8
UPDATE movies SET collection_id = (SELECT id FROM collections WHERE slug = '90s-romance')
WHERE id IN (966, 171, 685, 160, 1734, 1713, 1005, 601);

-- 3. SF 클래식 — SF 태그 + release_year < 2010, 평점순 top 8
--    (프레스티지=229는 놀란 컬렉션 우선 배정으로 여기서 제외됨)
UPDATE movies SET collection_id = (SELECT id FROM collections WHERE slug = 'sf-classics')
WHERE id IN (451, 194, 342, 180, 139, 278, 845, 126);

-- 4. 가족과 함께 — 가족/애니메이션 태그, 평점순 top 8
--    (한자 원제 미번역작 제외 — 仙逆剧场版 등 TMDB 한글 타이틀 미확보작)
UPDATE movies SET collection_id = (SELECT id FROM collections WHERE slug = 'family-picks')
WHERE id IN (15, 88, 636, 220, 59, 96, 93, 653);

-- 5. 액션의 정수 — 액션 태그, 평점순 top 8
--    (다크나이트=99·인셉션=106은 놀란 컬렉션 우선 배정, 스타워즈5=451은
--    SF 클래식 우선 배정으로 여기서 제외됨. 가족/애니메이션 중복 태그작도 제외)
UPDATE movies SET collection_id = (SELECT id FROM collections WHERE slug = 'action-essentials')
WHERE id IN (115, 750, 651, 141, 80, 319, 154, 862);

-- 검증 — 컬렉션별 배정 편수 + 컬렉션 간 중복 배정 0건 확인
SELECT c.slug, c.name, count(m.id) AS movie_count
FROM collections c LEFT JOIN movies m ON m.collection_id = c.id
GROUP BY c.slug, c.name
ORDER BY c.slug;
