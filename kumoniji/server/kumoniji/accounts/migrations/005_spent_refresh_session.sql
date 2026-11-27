-- 세션을 지우면 ON DELETE CASCADE가 spent_refresh.session_id로 이력을 찾는다. 인덱스가 없으면 지우는 세션마다
-- 이력 테이블 전체를 훑는다 — 30일 안 쓴 세션을 주기적으로 한꺼번에 지우게 되면서 필요해졌다.
CREATE INDEX spent_refresh_session ON spent_refresh (session_id);
