# 쿠모니지 계정 — SECURITY.md 1·2절 전부 (계획 B)

> **상태(11-21):** 서버·웹 앱 구현 완료, 검증 기록은 `../security-verification.md`. 계획과 다른 점은 아래 3가지(`security-verification.md` 예외 표에 정리).
> - 휴대폰 앱의 Keystore 보관·google_sign_in·MFA QR은 안드로이드 출시 전으로 미뤘다.
> - 웹 구글 로그인은 서버 리디렉트 방식으로 했다.
> - 기기 목록은 API만 만들었다.

**Goal:** 이메일 가입·구글 로그인·세션·MFA·복구·주소 변경·새 기기 알림·탈퇴를 SECURITY.md 1·2절(검증 1~13)대로 만들고, **싱글·멀티 모두 로그인한(인증된) 사람만** 쓰게 한다.

**Architecture:** 쿠모니지 서버(FastAPI) 안에 `accounts/` 패키지를 둔다(별도 서비스 X — 파드 하나 유지). 상태는 **새 Postgres 컨테이너**(`kumoniji-db`)에만 둔다. Redis는 쓰지 않는다(SECURITY 12: Redis를 유일한 폐기·시도 제한 저장소로 쓰지 말 것 → 시도 제한도 Postgres). SQL은 psycopg 3로 직접 쓰고, 마이그레이션은 번호 붙은 `.sql` 파일을 시작 때 적용한다(ORM·alembic 없음). 웹은 `__Host-` 쿠키, 앱은 보안 저장소의 리프레시 토큰.

**Tech Stack:** psycopg[binary] 3 · argon2-cffi · pyjwt[crypto](구글 ID 토큰·자체 액세스 토큰) · pyotp(TOTP) · cryptography(Fernet, TOTP 비밀 암호화) · httpx(HIBP·구글 토큰 교환) · smtplib(표준 라이브러리) / Flutter: flutter_secure_storage · google_sign_in(앱) · qr_flutter(MFA 등록 QR)

## Global Constraints
- 범위: SECURITY.md **1절(가입·인증·복구)·2절(외부 로그인·세션)** 전부, 검증 번호 1~13. 결제(3절)·관리자(24)·백업(6절)은 범위 밖.
- 웹 보안 머리글·CSRF·CORS(25~27)와 서비스 거부 예산(30)은 **로그인 API에 필요한 만큼** 같이 넣는다(로그인 쿠키를 쓰는 순간 CSRF 없이는 1·2절을 지킬 수 없음).
- 메일 발신: 당분간 아침 메일과 같은 Gmail 계정·앱 비밀번호(`NEWS_DIGEST_SMTP_USER`/`PASSWORD`와 같은 값을 쿠모니지 `.env`에 사용자가 넣음). **보낸 사람 주소는 설정값**(`KUMONIJI_MAIL_FROM`) — 도메인을 사면 바꾼다(11-21 사용자 결정). SPF·DKIM·DMARC(31)는 Gmail이 맡으므로 도메인 메일로 옮길 때 다시 본다.
- Apple 로그인·Apple 토큰 취소는 아이폰 출시 때(지금은 웹·안드로이드). 검증 기록에 Apple 항목은 "해당 없음".
- 비밀번호: 15~128자, 조합 강제 없음, 이메일·닉네임과 같으면 거부, HIBP k-익명성(앞 5자리만). 조회 장애 → 로컬 유출 목록(`pwned_top.txt`, 상위 10만 개 SHA-1) → 그것도 없으면 가입·변경·재설정 보류(기존 로그인은 유지).
- argon2id: m=65536(64MB)·t=3·p=1에서 시작, 노트북 실측 ~0.3초로 조정, 로그인 때 재해시. 동시 해시 작업 세마포어 2(파드 메모리 한도 → 512Mi로 올림).
- 토큰 수명: 액세스 15분(JWT, HS256, `typ=access`), 리프레시 유휴 30일·절대 만료 없음(ADR-0017, 불투명 32바이트, DB엔 SHA-256만), 가입 인증 24시간, 재설정 30분, 옛 주소 보호 링크 7일, 최근 인증 5분.
- 매 보호 요청에서 Postgres의 세션 폐기 상태·계정 인증 버전을 확인(SECURITY 12). DB 확인 실패 → 거부.
- 무료만. 새 비용 없음.
- **싱글도 로그인 필수**(11-21 사용자 결정). 앱을 켜면 로그인 화면부터, 한 번 로그인하면 그 계정으로 **자동 로그인 유지** — 리프레시가 살아 있는 동안(30일 동안 안 쓰면 만료, 절대 만료 없음 — ADR-0017) 앱을 다시 열어도 로그인 화면 없이 메인으로. 만료되면 로그인 화면.
- 싱글 판도 계정에 묶는다: `Room`에 `account_id`, 판 조회·수 두기는 그 계정만(다른 계정은 404). IP당 판 생성 제한은 계정당으로 바꾼다.

## 사용자 선행 작업 (PR은 머지 보류하고 알림)
1. **새 Postgres 컨테이너**: `kumoniji/db/docker-compose.yaml`(커밋됨, 프로젝트 이름 `kumoniji`, 볼륨 `kumoniji_db_data`, 포트 5433)로 Claude가 띄운다 — 실행 직전 한 번 더 확인받는다.
2. **구글 OAuth 클라이언트**: Google Cloud 콘솔에서 쿠모니지용 OAuth 클라이언트(웹), 승인된 리디렉션 URI `https://kumoniji.suvisdev.cloud/api/auth/google/callback`. 안드로이드는 Android 클라이언트(패키지 `cloud.suvisdev.kumoniji`·서명 SHA-1) — 등록한 뒤 `.env`에 `KUMONIJI_GOOGLE_ANDROID=1`을 넣어야 앱에 구글 버튼이 보인다(11-27).
3. **Cloudflare Turnstile**(무료 CAPTCHA, SECURITY 4): 사이트 키·비밀 키.
4. `kumoniji/.env`(gitignore) — `deploy.sh`가 Secret `kumoniji-env`로 넣는다:
   `KUMONIJI_DATABASE_URL`, `KUMONIJI_JWT_SECRET`, `KUMONIJI_TOTP_KEY`(Fernet), `KUMONIJI_GOOGLE_CLIENT_ID/SECRET`, `KUMONIJI_TURNSTILE_SITE/SECRET`, `KUMONIJI_SMTP_USER/PASSWORD`, `KUMONIJI_MAIL_FROM`, `KUMONIJI_PUBLIC_ORIGIN=https://kumoniji.suvisdev.cloud`

---

## 파일 구조

```text
kumoniji/
├── db/docker-compose.yaml          # kumoniji-db (postgres:16-alpine, 5433, 볼륨 kumoniji_db_data)
├── .env.example                    # 위 키 목록(값 없음)
├── deploy.sh                       # + .env → Secret kumoniji-env
├── k8s.yaml                        # + envFrom secretRef, hostAliases(host.docker.internal→10.42.0.1)
└── server/
    ├── requirements.txt            # + psycopg[binary] argon2-cffi pyjwt[crypto] pyotp cryptography httpx
    ├── kumoniji/accounts/
    │   ├── db.py                   # 연결 풀, migrate(), tx()
    │   ├── migrations/001_accounts.sql
    │   ├── passwords.py            # 정책·HIBP·argon2id(세마포어)
    │   ├── tokens.py               # 1회용 토큰 발급·원자 소비, JWT 액세스, 리프레시 회전
    │   ├── limits.py               # 시도 제한(계정 지수 지연·IP·전체 예산) — Postgres
    │   ├── mail.py                 # SMTP 비동기 큐, 템플릿(피싱 방지 문구)
    │   ├── google.py               # 웹: 인가 코드+PKCE+state+nonce / 앱: ID 토큰 검증
    │   ├── mfa.py                  # TOTP 등록·확인·교체·해제, 복구 코드 10개
    │   ├── service.py              # 가입·인증·로그인·복구·주소 변경·연결/해제·탈퇴
    │   ├── web.py                  # 라우터 /api/auth/*, 쿠키·CSRF·Origin 검사
    │   ├── deps.py                 # current_user(): 액세스 검증 + DB 세션 확인 + 최근 인증·MFA 단계
    │   └── headers.py              # CSP·frame-ancestors·nosniff·no-store 미들웨어
    └── tests/accounts/             # 검증 번호별 테스트(실제 Postgres, 테스트마다 임시 DB)
└── app/lib/account/                # 로그인·가입·인증·재설정·MFA·계정 설정 화면
```

## 스키마 (`001_accounts.sql`)

```sql
CREATE TABLE accounts (
  id            bigserial PRIMARY KEY,
  email         text,                       -- 정규화(앞뒤 공백 제거·도메인 소문자)
  email_key     text,                       -- 비교용(전체 소문자). 점·+별칭은 그대로
  nickname      text NOT NULL,
  pw_hash       text,
  verified_at   timestamptz,                -- NULL = 미인증(대국 금지)
  auth_version  integer NOT NULL DEFAULT 1, -- 올리면 모든 세션·액세스·미소비 토큰 무효
  mfa_secret    bytea,                      -- Fernet 암호문
  mfa_enabled   boolean NOT NULL DEFAULT false,
  mfa_last_step bigint,                     -- 같은 시간 단계 재사용 금지
  deleted_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX accounts_email_key ON accounts (email_key) WHERE deleted_at IS NULL;
CREATE TABLE identities (provider text, sub text, account_id bigint NOT NULL REFERENCES accounts, PRIMARY KEY (provider, sub));
CREATE TABLE auth_tokens (
  hash bytea PRIMARY KEY, account_id bigint NOT NULL REFERENCES accounts,
  purpose text NOT NULL, target text, version integer NOT NULL,
  expires_at timestamptz NOT NULL, used_at timestamptz
);
CREATE TABLE sessions (
  id uuid PRIMARY KEY, account_id bigint NOT NULL REFERENCES accounts,
  refresh_hash bytea NOT NULL UNIQUE, prev_hash bytea,   -- 재사용 탐지
  device text, ip inet, created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz NOT NULL DEFAULT now(), reauth_at timestamptz NOT NULL,
  mfa_passed boolean NOT NULL, revoked_at timestamptz
);
CREATE TABLE recovery_codes (account_id bigint REFERENCES accounts, hash bytea, used_at timestamptz, PRIMARY KEY (account_id, hash));
CREATE TABLE attempts (key text PRIMARY KEY, fails integer NOT NULL, until timestamptz);
CREATE TABLE known_devices (account_id bigint REFERENCES accounts, device_hash bytea, PRIMARY KEY (account_id, device_hash));
CREATE TABLE deletion_log (account_ref bytea PRIMARY KEY, requested_at timestamptz NOT NULL);  -- HMAC(id), 백업 복원 뒤 재삭제
```

---

## 태스크 (각각 실패 테스트 → 구현 → 통과 → 커밋. 테스트 이름에 검증 번호)

### Task 1: DB 컨테이너·연결·마이그레이션
- compose 파일, `db.migrate()`가 `schema_version`을 보고 남은 `.sql`만 적용.
- `tests/accounts/conftest.py`: `KUMONIJI_TEST_DATABASE_URL`로 테스트마다 `CREATE DATABASE t_<uuid>` → migrate → DROP. CI 쿠모니지 server 잡에 `services: postgres:16`.
- 테스트: migrate 두 번 = 같은 결과(멱등), 표 목록.

### Task 2: 비밀번호 정책·해시 (검증 2)
- `passwords.check(pw, email, nickname) -> None | 이유`, `hash(pw)`, `verify(h, pw) -> (ok, new_hash | None)`.
- 테스트: 14자·129자 거부, 공백 포함 15자 문장 허용, 이메일·닉네임과 같으면 거부, HIBP 접미사 일치 거부(httpx MockTransport), HIBP 장애 → 로컬 목록, 둘 다 없음 → `"unavailable"`, 해시 파라미터 m=65536·t=3·p=1, 약한 파라미터 해시는 verify가 새 해시 반환, DB에 원문 없음.

### Task 3: 1회용 토큰 (검증 3)
- `tokens.issue(conn, account_id, purpose, target, ttl) -> str`(32바이트 urlsafe, DB엔 SHA-256, 같은 계정·목적 이전 토큰 무효), `tokens.consume(conn, raw, purpose, target=None) -> account_id | None`:
```sql
UPDATE auth_tokens t SET used_at = now()
FROM accounts a
WHERE t.hash = $1 AND t.purpose = $2 AND t.used_at IS NULL AND t.expires_at > now()
  AND a.id = t.account_id AND t.version = a.auth_version AND ($3::text IS NULL OR t.target = $3)
RETURNING t.account_id;
```
- 테스트: 20스레드 동시 소비 중 1개만 성공, 다른 목적·대상·만료·옛 버전 거부, 재발급 뒤 이전 토큰 거부.

### Task 4: 시도 제한·CAPTCHA·응답 균일화 (검증 4)
- `limits.check_and_hit(conn, keys) -> wait_seconds`: 5회 실패 뒤 2^(n-5)초, 최대 900초, 영구 잠금 없음. 키 `acct:<email_key>`·`ip:<ip>`·`all`(분당 전체 예산). 입력 바이트 상한(이메일 254, 비밀번호 128자·512바이트)을 해시 전에. 같은 IP 10회 실패면 Turnstile 요구.
- 가입·로그인·재설정은 계정 유무와 무관하게 같은 코드·문구, 없는 계정도 더미 해시 검증, 메일은 큐.
- 테스트: 6번째 실패 지연 1초·상한 900초, 존재/미존재 계정 각 50회 코드·본문 동일·시간 중앙값 차이 < 50ms, 긴 입력은 해시 호출 없이 거부.

### Task 5: 가입·인증·선점 회수 (검증 1)
- `POST /api/auth/signup {email, password, nickname, turnstile?}` → 항상 202. 인증된 계정이 이미 있으면 그 주소로 "이미 가입됨" 메일만. 미인증 계정이 있으면 새 인증 메일.
- `GET /verify?token=`은 확인 화면만(메일 스캐너의 GET이 소비 못 함), `POST /api/auth/verify {token, password}`가 소비. 선점 상태였으면 같은 트랜잭션에서 비밀번호를 이 요청의 값으로 교체, identities·MFA·복구 코드·세션·미소비 토큰 삭제·폐기, `auth_version+1` 뒤 `verified_at`.
- 미인증 24시간 지난 계정 정리(시작 때 + 1시간마다).
- 테스트: `A@x.com`·`a@X.com` 동시 가입 → 활성 1개, 미인증 계정 대국 API 403, 선점 계정 인증 뒤 선점자 비밀번호·세션·연결 무효, 무효화 중 오류면 `verified_at` NULL 유지(롤백).

### Task 6: 세션·액세스·리프레시 회전·쿠키 (검증 11·12·13)
- 로그인 → `sessions` 행 + 액세스 JWT(`sub, sid, ver, typ=access, iss, aud, exp`) + 리프레시. 웹: `__Host-kat`·`__Host-krt` HttpOnly·Secure·SameSite=Lax·Path=/, localStorage 안 씀. 앱: JSON으로 받아 flutter_secure_storage(Android `allowBackup=false`).
- `POST /api/auth/refresh`:
```sql
UPDATE sessions SET prev_hash = refresh_hash, refresh_hash = $new, last_used_at = now()
WHERE refresh_hash = $old AND revoked_at IS NULL
  AND last_used_at > now() - interval '30 days'
RETURNING id, account_id;
```
  0행이고 `prev_hash = $old`인 세션이 있으면 재사용 → 그 계정 전 세션 폐기 + 알림 메일. `reauth_at`은 갱신으로 안 늘림.
- `deps.current_user`: alg=HS256 고정·iss·aud·exp·typ 검사 → 세션 `revoked_at IS NULL`·`auth_version == ver`·`deleted_at IS NULL`·(필요 시) `mfa_passed`, DB 오류면 401.
- 앱 갱신 직렬화: `Api`가 진행 중인 갱신 Future 하나를 공유.
- 테스트: 29일 쉬었다 갱신 성공·31일이면 401, 만든 지 1년 된 세션도 매일 쓰면 갱신 성공, 같은 리프레시 두 번 → 두 번째에 전 세션 폐기, 리프레시를 액세스로 쓰면 401, alg none·다른 키·만료·iss/aud 변조 401, 로그아웃 직후 같은 액세스 401, 쿠키 속성 문자열.

### Task 7: CSRF·Origin·보안 머리글 (검증 26·27, 25 일부)
- 쿠키 인증 상태 변경 요청은 `Origin == KUMONIJI_PUBLIC_ORIGIN` + 이중 제출 CSRF(`__Host-kcsrf` 쿠키 = `X-CSRF` 머리글). 로그인·로그아웃·연결 포함. 앱(Bearer)은 쿠키 없음 → 면제.
- 머리글: CSP(Flutter 웹 빌드 실측으로 최소 허용, frame-ancestors 'none', object-src 'none', base-uri 'none'), `X-Frame-Options: DENY`, `nosniff`, 인증 응답 `no-store`, 복구 화면 `Referrer-Policy: no-referrer`. 먼저 Report-Only로 배포해 위반 0 확인 뒤 차단 모드.
- 테스트: 다른 Origin POST 403, CSRF 머리글 없음 403, 머리글 값, Playwright로 CSP 아래 앱 정상 표시.

### Task 8: 구글 로그인·연결/해제 (검증 9·10)
- 웹: `GET /api/auth/google/start` → state·nonce·PKCE verifier를 서명된 10분 쿠키 `__Host-kgo`에 두고 302. `GET /api/auth/google/callback` → state 일치·code 교환(verifier)·ID 토큰 검증(JWKS, RS256만, iss ∈ {accounts.google.com, https://accounts.google.com}, aud, exp, nonce, `email_verified`). 리디렉트 URI 고정 상수.
- 앱: `POST /api/auth/google/app {id_token, nonce}` 같은 검증.
- (google, sub)가 없으면 새 계정(같은 이메일 자체 계정이 있어도 자동 병합 안 함 — 새 계정 이메일 칸은 비우고 "기존 계정이면 로그인 후 설정에서 연결" 안내).
- 연결: 로그인 + 5분 재인증 + MFA(켜져 있으면) + 새 구글 인증. 해제: 재인증·MFA, 마지막 로그인 수단이면 거부.
- 테스트: 잘못된 키·alg·iss·aud·nonce·state·만료 거부(테스트 RSA 키로 JWKS 모킹), 같은 이메일 자체 계정 있으면 새 계정 생성·기존 계정 그대로, 마지막 수단 해제 거부, 제공자가 다른 같은 sub 구분.

### Task 9: 재설정·로그인 중 비밀번호 변경 (검증 5)
- `POST /api/auth/reset/request {email}` → 항상 202, 계정 있으면 30분 토큰 메일(링크는 공개 원점 고정, Host 머리글 안 씀). `GET`은 화면만, `POST /api/auth/reset {token, password}` → 교체·`auth_version+1`·알림·자동 로그인 없음·MFA 유지.
- 로그인 중 변경: 5분 재인증 + MFA.
- 테스트: 30분 뒤·재사용 거부, 재설정 뒤 기존 액세스·리프레시 401, MFA 계정은 재설정 뒤에도 TOTP 필요, Host 변조해도 링크 원점 고정, GET 두 번에도 미소비.

### Task 10: MFA (검증 7)
- 등록: 5분 재인증 → 비밀 생성·암호화 저장(비활성) → 새 코드 확인 시 활성 + 복구 코드 10개(한 번만 표시, 해시 저장) + 알림.
- 로그인: 1차 인증 뒤 MFA 켜져 있으면 `mfa_passed=false` 세션 — MFA·복구 API 외 403. 코드는 `valid_window=1` + `mfa_last_step`보다 큰 단계만 + 시도 제한.
- 교체: 재인증 + 기존 코드 + 새 코드. 해제·재발급: 재인증 + 기존 코드 또는 복구 코드, 이전 코드 폐기. 복구 코드 사용은 `UPDATE ... WHERE used_at IS NULL RETURNING`.
- 이메일만으로 MFA를 끄는 경로 없음(전부 분실은 수동 절차 — 출시 전 확정, 문서로).
- 테스트: 미확인 비밀 비활성, 5분 지난 재인증 거부, 같은 코드 두 번 거부, 창 밖 거부, 복구 코드 동시 사용 1개만, 재발급 뒤 이전 코드 무효, MFA 전 세션으로 연결·대국 403.

### Task 11: 주소 변경·새 기기 알림·보호 요청 (검증 6)
- 변경: 재인증 + MFA + 새 주소 인증 토큰(target=새 주소). 확인 시 교체 + 옛 주소에 7일 보호 링크 — 로그인·복원 권한 없음, 누르면 보호 요청(민감 작업 잠금·전 세션 폐기·`auth_version+1`, 이후 수동 복구).
- 새 기기: `device_hash = sha256(앱 설치 ID 또는 UA 요약)`가 `known_devices`에 없으면 알림(기기·`CF-IPCountry` 나라·시간·"내가 아니면" = 보호 요청 링크).
- 테스트: 연속 두 번 변경 뒤 첫 토큰 거부, 보호 링크로 로그인·복원 안 됨, 보호 요청 뒤 전 세션 401, 새 기기 메일이 큐에.

### Task 12: 탈퇴 (검증 8)
- `POST /api/auth/delete` 재인증 + MFA → 한 트랜잭션: `deleted_at`·`auth_version+1`·세션 폐기·`deletion_log`. 이후 개인정보 지우기(email·nickname·pw_hash·mfa·identities·known_devices)는 재시도 작업(시작 때·1시간마다). 결제·원장 없음. 제재 기록 보관 근거 미확정 → 탈퇴 시 파기.
- 시작 때 `deletion_log`에 있는데 살아 있는 계정은 다시 지움(백업 복원 대비).
- 테스트: 탈퇴 직후 액세스·리프레시·웹소켓 401, 같은 이메일 재가입 가능, 행 되살린 뒤 시작 루틴이 다시 지움.

### Task 13: 메일
- `mail.send(to, kind, link, lang)` → 큐(스레드 1개, 3회 재시도, 로그에 주소·링크 안 남김). ko/en/ja 템플릿, 끝에 "비밀번호·인증번호·복구 코드는 이메일 회신이나 상담으로 요구하지 않습니다. 의심되면 앱이나 공식 주소로 직접 접속하세요." 링크는 공개 원점 HTTPS, 단축 URL 없음, 입력값 이스케이프.
- 테스트: 문구 포함, 원점 고정, SMTP 실패해도 API 응답 동일, 로그에 토큰 없음.

### Task 14: 앱 화면
- 앱 시작: 저장된 세션으로 `GET /api/auth/me`(필요하면 갱신 한 번) → 성공이면 메인, 아니면 로그인 화면. 싱글·멀티 모두 로그인 뒤에만 보인다. 설정에 로그아웃.
- 화면: 로그인(이메일·비밀번호 / 구글), 가입, "메일을 확인하세요", 인증 확인(링크 → 버튼으로 POST), 재설정 요청·재설정, MFA 코드, 설정 > 계정(닉네임, 비밀번호·주소 변경, MFA 등록·해제·복구 코드, 구글 연결·해제, 로그인된 기기·개별 로그아웃, 탈퇴).
- 웹은 쿠키 + CSRF 머리글(앱 코드가 토큰을 안 만짐), 안드로이드는 Bearer + secure storage.
- 위젯 테스트: 세션이 살아 있으면 로그인 화면 없이 메인, 만료(갱신 401)면 로그인 화면, 로그인 실패 문구가 계정 유무와 무관하게 같음, MFA 필요 응답이면 코드 화면, 401이면 갱신 한 번 후 재시도.

### Task 14-1: 싱글 판을 계정에 묶기
- `/api/games*`에 `current_user` 의존성, `Room.account_id`, 다른 계정 접근 404, 생성 제한 계정당 분당 30.
- 테스트: 로그인 없이 판 만들기 401, 남의 판 조회·수 두기 404, 미인증 계정 403.

### Task 15: 배포·검증 기록
- `deploy.sh`: `.env` 없으면 실패, Secret 갱신. `k8s.yaml`: envFrom·hostAliases·메모리 512Mi. replicas는 여전히 1(멀티 판이 메모리에 있음 — 계획 C).
- `kumoniji/_docs/security-verification.md`: 검증 1~13 결과표(실행일·환경·통과/실패/미실행·증거). 13(쿠키·형제 도메인 주입)은 Playwright 실측.
- 머지 보류: 새 환경 변수·DB → 사용자 확인 후 `confirm-prereq`.
