-- 회전된 리프레시 토큰 이력. 직전 하나(prev_hash)만 기억하면 주인이 두 번 갱신한 뒤의 탈취 토큰 재사용을 못 알아챈다.
-- 30일(유휴 만료와 같음) 뒤 정리한다 — 그 토큰은 회전되지 않았더라도 그때 만료됐을 것이다.
CREATE TABLE spent_refresh (
  hash       bytea PRIMARY KEY,
  session_id uuid NOT NULL REFERENCES sessions ON DELETE CASCADE,
  spent_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX spent_refresh_at ON spent_refresh (spent_at);
DROP INDEX sessions_prev;
ALTER TABLE sessions DROP COLUMN prev_hash;
