-- 계정·세션(SECURITY.md 1·2절). 계획 B(kumoniji/_docs/plans/2026-11-21-B-accounts.md) 스키마.
CREATE TABLE accounts (
  id            bigserial PRIMARY KEY,
  email         text,
  email_key     text,
  nickname      text NOT NULL,
  pw_hash       text,
  verified_at   timestamptz,
  auth_version  integer NOT NULL DEFAULT 1,
  mfa_secret    bytea,
  mfa_enabled   boolean NOT NULL DEFAULT false,
  mfa_last_step bigint,
  locked_at     timestamptz,
  deleted_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX accounts_email_key ON accounts (email_key) WHERE deleted_at IS NULL;
CREATE TABLE identities (
  provider   text NOT NULL,
  sub        text NOT NULL,
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  PRIMARY KEY (provider, sub)
);
CREATE TABLE auth_tokens (
  hash       bytea PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  purpose    text NOT NULL,
  target     text,
  version    integer NOT NULL,
  expires_at timestamptz NOT NULL,
  used_at    timestamptz
);
CREATE INDEX auth_tokens_account ON auth_tokens (account_id, purpose);
CREATE TABLE sessions (
  id           uuid PRIMARY KEY,
  account_id   bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  refresh_hash bytea NOT NULL UNIQUE,
  prev_hash    bytea,
  device       text,
  ip           text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz NOT NULL DEFAULT now(),
  reauth_at    timestamptz NOT NULL,
  mfa_passed   boolean NOT NULL,
  revoked_at   timestamptz
);
CREATE INDEX sessions_account ON sessions (account_id);
CREATE INDEX sessions_prev ON sessions (prev_hash);
CREATE TABLE recovery_codes (
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  hash       bytea NOT NULL,
  used_at    timestamptz,
  PRIMARY KEY (account_id, hash)
);
CREATE TABLE attempts (
  key   text PRIMARY KEY,
  fails integer NOT NULL,
  until timestamptz,
  seen  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE known_devices (
  account_id  bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  device_hash bytea NOT NULL,
  PRIMARY KEY (account_id, device_hash)
);
CREATE TABLE deletion_log (
  account_ref  bytea PRIMARY KEY,
  account_id   bigint NOT NULL,
  requested_at timestamptz NOT NULL DEFAULT now(),
  purged_at    timestamptz
);
