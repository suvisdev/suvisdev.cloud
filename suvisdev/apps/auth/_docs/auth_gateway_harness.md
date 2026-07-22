AUTH-GATEWAY-HARNESS.md

인증 게이트웨이(auth.suvisdev.cloud) 분리 배포 — 구현 완료 기록
대상 저장소: suvisdev.cloud 모노레포 (apps/ 하위 멀티앱 구조, Clean Architecture)
원칙: 기존 구조 무변경, 추가만 허용. 발급은 auth 서비스에서만, 다른 앱은 검증만.

---

0. 컨텍스트

- `api.suvisdev.cloud`는 `apps/viewer`가 자체 OAuth(Google/Kakao/Naver)/JWT(HS256)/Redis
  세션/RBAC(`require_admin`)로 서비스 중 — 그대로 무변경, 실서비스 로그인 경로로 계속 사용.
- 이번 작업은 같은 코드베이스에 `apps/auth`를 새 병렬 게이트웨이로 구축한 것 — RS256
  비대칭키로 발급하고, 다른 앱은 공개키로만 검증한다.
- **이번 라운드는 순수 병렬 구축이다.** `auth` 컨테이너는 뜨고 테스트도 통과하지만
  실트래픽에는 아직 연결되지 않는다 — cloudflared 라우팅, `suvis` 프론트엔드, viewer
  코드 변경은 전부 범위 밖(추후 별도 작업, Strangler Fig 전환).
- 네트워크: docker-compose 기본(암묵적) 네트워크에 `auth` 서비스가 `redis`/`db`와
  같이 묶여 있다. 호스트 포트는 노출하지 않는다.
- 키 체계: RS256 비대칭. 개인키(`JWT_PRIVATE_KEY_B64`)는 `auth` 컨테이너의
  `.env.auth`에만 존재.

1. 절대 규칙 (실제로 지킨 것)

- `apps/viewer` 하위 기존 코드는 한 줄도 수정하지 않았다.
- 어떤 기존 서비스에도 호스트 포트 노출을 추가하지 않았다 — `auth` 서비스도 `ports:` 없음.
- JWT 검증부의 허용 알고리즘은 `algorithms=["RS256"]` 리터럴로 하드코딩(`apps/auth/security.py`,
  `shared/security/token_verifier.py`).
- 개인키를 읽는 코드는 발급 함수(`apps/auth/security.py`의 `_load_private_key`, 호출 시점에만
  읽음)에만 존재 — 검증 경로(`verify`, `shared/security/token_verifier.py`)는 공개키만 읽는다.
- 비밀키·개인키는 커밋하지 않음. `.env.auth`/`*.pem`은 기존 `suvisdev/.gitignore`
  (`.env.*`, `*.pem`)에 이미 걸려 있어 추가 수정 불필요.
- `contents, dispatch, gildle, mova, ontology, sample, silicon_valley, titanic, viewer`는
  `auth`를 import하지 않는다 — `.importlinter`의 `auth-isolation`/`spoke-independence`
  계약으로 강제. 다른 앱이 토큰 검증에 쓸 수 있는 건 `shared.security`뿐.

2. 실제 구현 — 최종 구조 (헥사고날 레이어 대신 평탄한 구조로 단순화)

```
apps/auth/
├── __init__.py
├── rbac.py            # Role(StrEnum): ADMIN/USER, Permission, ROLE_PERMISSIONS
├── security.py         # JwtAdapter(RS256 발급/검증) + get_current_user/RoleChecker(auth 자체용, 미사용 대기)
├── repository.py       # AuthMirrorBase + UserMirror/AdminMirror/UserIdentityMirror/GroupMirror
│                       # (users/admins/user_identities/groups 테이블 read-only 조회 — viewer ORM 미import)
│                       # + User 값 객체 + UserRepository
├── oauth_adapters/
│   ├── __init__.py     # OAuthIdentity, OAuthError (공용 타입)
│   ├── google.py / kakao.py / naver.py   # viewer 어댑터와 별개로 새로 작성, AUTH_*_REDIRECT_URI 사용
├── refresh_store.py    # RefreshTokenStore(Redis, "auth:" 키 접두사) — rotate 시 재사용 감지 → family 폐기
├── services.py          # AuthService — login/refresh/logout/oauth_callback 오케스트레이션
├── router.py            # POST /auth/login,/logout,/refresh, GET /auth/callback/{provider}, GET /.well-known/jwks.json
├── schemas.py           # LoginRequest(aud 포함)/RefreshRequest/TokenResponse/TokenPayload
└── tests/               # 23개 테스트 — 아래 4번 참고

auth_main.py             # 루트, main.py 옆 — docs_url=None, /healthz, auth.router 등록

shared/security/token_verifier.py   # verify_token(token, aud) — JWT_PUBLIC_KEY_B64만 사용,
                                      # apps.auth를 import하지 않고 독립 구현(격리 유지)

apps/mova/dependencies/require_auth.py         # get_current_user + RoleChecker(shared.security만 import)
apps/mova/adapter/inbound/api/v1/whoami_router.py   # GET /mova/whoami — RBAC 패턴 데모(신규 엔드포인트 1개)
```

- DB 접근: `apps/auth`는 `users`/`admins`/`user_identities`/`groups`를 **자체 read-only
  mirror ORM**(별도 `DeclarativeBase`)으로 조회한다. 테이블 소유권(DDL/Alembic)은 100%
  `apps/viewer`에 남고, `apps/auth`는 `create_all`/`drop_all`을 호출하지 않는다. 물리적으로는
  `core.matrix.grid_oracle_database_manager.get_viewer_session_factory()`를 그대로 재사용.
  → 부수 효과: 아직 신규 유저를 만들 수 없음 — `GET /auth/callback/{provider}`는 viewer
  쪽에서 이미 연동된 identity만 성공(미연동 시 409). 회원가입은 범위 밖.
- 비밀번호 검증: 기존 `admins`/`users.password_hash`가 sha256이라
  `_verify_legacy_sha256_password()`로 그 규칙(sha256 다이제스트 + 레거시 평문 폴백)을
  그대로 재현. bcrypt로 "고치면" 기존 계정 로그인이 깨지므로 그대로 둘 것.
- Role enum은 `viewer.app.dtos.role.UserRole`을 import하지 않고 `apps/auth/rbac.py`에
  독립적으로 정의(의도적 중복 — import-linter 격리 방향 때문).
- RoleChecker도 `apps/auth/security.py`(auth 자체용, 미사용 대기)와
  `apps/mova/dependencies/require_auth.py`(실제 데모)에 각각 독립적으로 존재 —
  mova가 `apps.auth`를 import하면 격리 계약 위반이 되므로 작게 중복시켰다.
- aud는 서비스별로 상이하게 발급(예: `suvis-mova`, `suvis-gildle`) — `LoginRequest`/
  `callback`이 `aud`를 받아 그 값으로 토큰을 발급한다. 이번 라운드에 실제로 검증하는
  곳은 `apps/mova`의 `/mova/whoami` 데모 하나.
- Redis: `apps/viewer`와 같은 `redis` 서비스(`redis://redis:6379/0`)를 재사용하고,
  키 접두사만 `auth:`로 분리(`viewer:session:*` 등과 충돌 없음).

3. docker-compose.yaml / .importlinter / .env

- `docker-compose.yaml`에 `auth` 서비스 추가 — `backend`와 같은 이미지/빌드 컨텍스트
  재사용, `command: uvicorn auth_main:app --host 0.0.0.0 --port 9000`만 다름. `ports:` 없음.
  `DATABASE_URL`과 `MOVA_DATABASE_URL` 둘 다 `db:5432`로 덮어써야 한다 —
  `get_viewer_session_factory()`가 `MOVA_DATABASE_URL`을 `DATABASE_URL`보다 우선
  참조하기 때문에(하나만 덮어쓰면 컨테이너 안에서 `.env`의 `localhost:5432` 값으로
  접속을 시도하다 실패한다 — 실제로 이 문제로 첫 배포가 500 에러났었음).
- `.importlinter`: `root_packages`에 `auth`/`shared` 추가, `spoke-independence`
  `modules`에 `auth` 추가(양방향 격리), 신규 계약 `auth-isolation`(9개 앱 → auth 금지)과
  `shared-independence`(shared → 어떤 스포크/auth도 금지) 추가.
- `.env.example`에 `JWT_PUBLIC_KEY_B64`/`JWT_KID`/`AUTH_{GOOGLE,KAKAO,NAVER}_REDIRECT_URI`
  추가. 실제 개인키는 `.env.auth`(신규, gitignore 적용)에만.
- `scripts/generate_jwt_keys.sh` — RS256 키페어 생성 + base64 출력.

4. 완료 기준 — 실제 검증 결과

- [x] `uvicorn auth_main:app` 단독 기동 성공, `/healthz` 200 — 실제 컨테이너(`suvisdev-auth-1`)로 확인.
- [x] `main.py`/`auth_main.py` 둘 다 `JWT_PRIVATE_KEY_B64` 없이 정상 동작(import 시점에 개인키 안 읽음).
- [x] `auth`가 발급한 토큰을 `shared.security.token_verifier`가 공개키만으로 검증 통과
      — 실제로 `auth` 컨테이너에서 로그인해 받은 토큰을 `backend` 컨테이너의
      `GET /mova/whoami`에 넣어 200 응답 확인(진짜 컨테이너 간 검증, mock 아님).
- [x] aud 불일치 토큰은 403/401 — `suvis-gildle` aud로 받은 토큰을 mova(`aud=suvis-mova`)에
      제출하면 401 확인.
- [x] 만료/서명변조/`alg=none`/HS256-강제(키 혼동 공격) 토큰 각각 거부 테스트 존재
      (`apps/auth/tests/test_security.py`).
- [x] 리프레시 토큰 재사용 시 세션 전체 폐기 — 유닛 테스트(`test_refresh_store.py`) +
      실제 컨테이너에서 재사용 401 확인.
- [x] `lint-imports` 통과(신규 계약 포함, pre-existing `hub-independence` 위반 1건은
      이 작업과 무관 — ontology→core→{dispatch,mova,titanic,viewer} 기존 결합).
- [x] `pytest` — auth 23개, mova whoami 3개, shared 2개 전부 통과. 기존 스위트 회귀 없음
      (titanic 4개 collection 에러, mova/dispatch 4개 실패는 이 작업 이전부터 있던 것으로 확인됨).

5. 수동 적용 필요 (코드 변경 아님, 아직 안 함)

- Google/Kakao/Naver 개발자 콘솔에 `AUTH_*_REDIRECT_URI` 신규 등록 안 함(viewer용
  기존 URI만 등록돼 있음) — 실제 브라우저 OAuth 플로우는 아직 테스트 못 함, 로그인
  API(`/auth/login`, password 방식)와 refresh/reuse-detection만 실컨테이너로 검증됨.
- cloudflared 대시보드에 `auth.suvisdev.cloud` 라우팅 추가 안 함 — 컨테이너는 내부
  네트워크에서만 접근 가능, 외부 노출 없음.
- `apps/viewer` → `apps/auth` 실전환(Strangler Fig)은 완전히 범위 밖 — 다음 작업.
