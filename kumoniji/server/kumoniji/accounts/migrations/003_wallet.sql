-- 화폐(계획 D·ADR-0024). 잔고는 wallets, 모든 증감은 ledger(같은 계정+kind+ref는 한 번만), 일일 미션 누적은 daily.
CREATE TABLE wallets (
  account_id    bigint PRIMARY KEY REFERENCES accounts ON DELETE CASCADE,
  coins         bigint  NOT NULL DEFAULT 0  CHECK (coins >= 0),
  gems          integer NOT NULL DEFAULT 0  CHECK (gems >= 0),
  hearts        integer NOT NULL DEFAULT 10 CHECK (hearts >= 0),
  hearts_at     timestamptz NOT NULL DEFAULT now(),
  attend_day    date,
  attend_streak integer NOT NULL DEFAULT 0
);
CREATE TABLE ledger (
  id         bigserial PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  kind       text NOT NULL,          -- game·stake·heart·attend·mission·bonus·buy
  ref        text NOT NULL,          -- 판 id, 날짜+미션 id 등
  coins      bigint  NOT NULL DEFAULT 0,
  gems       integer NOT NULL DEFAULT 0,
  hearts     integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (account_id, kind, ref)
);
CREATE TABLE daily (
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  day        date NOT NULL,
  counts     jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY (account_id, day)
);
