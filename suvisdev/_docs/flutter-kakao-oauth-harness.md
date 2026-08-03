# HARNESS — susu 카카오 모바일 로그인: 백엔드 (apps/auth)

> 이 문서는 백엔드(`apps/auth`) 구현 범위만 다룬다. 클라이언트(susu/Flutter) 쪽 요구사항과
> API 계약은 [`susu/_docs/flutter-kakao-oauth-harness.md`](../../susu/_docs/flutter-kakao-oauth-harness.md)를 본다.
> **이번 라운드는 문서 작성까지만 — 코드는 작성하지 않는다.**

## Goal
susu(Flutter)의 카카오 OAuth 로그인 결과(access token)를 받아 유저 검증과 JWT 발급을
자체 백엔드(`apps/auth`)에서 수행한다. **모바일 로그인과 웹 로그인을 저장/발급/폐기
경로까지 철저히 분리**한다. 모바일 refresh token은 Redis의 전용 namespace에 저장한다.

## Context — 착수 전 확인 사항 (반드시 준수)
- hexagonal clean DDD, FastAPI(`uvicorn main:app`). **titanic 앱이 baseline 컨벤션**
  (frozen dataclass VO, from_orm 팩토리, DIP 어댑터 스왑)이지만, **`apps/auth`는 titanic처럼
  `adapter/inbound`·`adapter/outbound` 디렉터리로 나뉜 구조가 아니다** — `router.py` /
  `services.py`(`AuthService`) / `repository.py` / `security.py`의 flat 구조이고, DI는
  `AuthService.__init__`의 optional 키워드 인자(`user_repository=`, `token_issuer=`,
  `refresh_store=`, `oauth_adapters=` 등, `apps/auth/services.py:33-42`)로 이미 이뤄지고
  있다. 새 포트/어댑터도 titanic 디렉터리를 그대로 옮기기보다 이 기존 패턴에 맞춘다.
- 데이터 흐름 규약: `Schema → DTO → App → VO → Entity → ORM → DB`. app 포트가 adapter
  스키마를 import하지 않게(DIP) — schema→DTO 변환은 router(adapter) 계층에서.
- **기존 자산 재사용(새로 만들지 말 것)**:
  - `apps/auth/security.py`의 `JwtAdapter` — RS256 발급/검증(`JWT_PRIVATE_KEY_B64`/
    `JWT_PUBLIC_KEY_B64`/`JWT_KID`). 수정 없이 그대로 재사용 가능.
  - **주의**: `apps/auth/oauth_adapters/kakao.py`의 `KakaoOAuthAdapter`는 이미 있지만,
    이건 웹 로그인용 authorization-code + OIDC id_token(JWKS 서명 검증) 방식이다.
    모바일(`kakao_flutter_sdk`)은 code가 아니라 access_token을 SDK가 직접 반환하므로
    이 어댑터를 그대로 재사용할 수 없다 — R2의 "access_token → kapi 검증" 흐름을 위한
    **별도 포트**(가칭 `KakaoMobileTokenVerifierPort`)가 필요하다. (아래 Appendix의
    OIDC 대체안을 쓰면 오히려 기존 웹 어댑터 방식과 유사해지므로, 그 경우엔 재사용
    여지가 커진다 — 단 이번 라운드는 out of scope.)
  - `apps/auth/refresh_store.py`의 `RefreshTokenStore`는 이미 Redis 로테이션(rotate
    시 재사용 감지 → family 전체 폐기)을 구현하지만, 키가 `auth:refresh:{jti}`
    (jti 기준 전역 네임스페이스, `refresh_store.py:47`)다. R3가 요구하는
    `auth:refresh:mobile:{userId}` / `auth:refresh:web:{userId}` 식의 **userId 기준
    네임스페이스는 아직 없다**. 기존 웹 로그인이 이 클래스를 그대로 쓰고 있으므로
    (`services.py:45,114-140`), 웹 쪽 키 스킴을 건드리지 않고 모바일 전용 클래스로
    분리하거나, 네임스페이스 파라미터를 추가하는 방식 중 하나를 택해야 함 — 기존
    소비자(웹 로그인) 회귀 여부를 반드시 확인.
  - `apps/auth/repository.py`: **`apps/auth`는 `users`/`user_identities` 등 테이블의
    DDL을 소유하지 않는다** — 소유권은 100% `apps/viewer`(Alembic도 viewer 쪽)에 있고,
    `apps/auth`는 `AuthMirrorBase`로 같은 DB를 비침습적으로 읽고 쓸 뿐이다
    (`repository.py:1-10`). 카카오 로그인 유저 upsert도 기존 `UserMirror`/
    `UserIdentityMirror` ORM 매핑을 그대로 쓰고, 스키마 변경이 필요하면 viewer 쪽에서
    마이그레이션해야 한다.
- Docker: `redis:7-alpine`(6379) 컨테이너가 이미 compose 스택에 있음.
- **착수 전 `apps/auth`와 `apps/titanic` 구조를 먼저 읽고 기존 포트/어댑터/DI 관례에
  맞출 것** (위 항목들이 그 결과다).

## Architecture (구현 대상 플로우)
```
[susu / Flutter] — 상세는 susu 쪽 문서 참고
  loginWithKakaoTalk() 또는 loginWithKakaoAccount()
    → OAuthToken(access token) 획득 (클라는 me() 호출 금지)
  POST /auth/kakao/mobile  { access_token }

[Backend / apps/auth]
  1) 카카오 검증: GET https://kapi.kakao.com/v2/user/me (Bearer access_token)
  2) 존재/유효 판단 → DB user upsert (최초 로그인 시 생성)
  3) 자체 JWT 발급 (access JWT + refresh token) via security.py
  4) refresh token을 Redis 모바일 namespace에 저장

[Redis]
  auth:refresh:mobile:{userId} → refresh token (TTL 부여)
```

## Requirements

### R2. 백엔드 검증
- access token으로 `kapi /v2/user/me` 호출해 검증된 유저 정보 확보. 실패/무효 토큰이면 401.
- 클라가 보낸 유저정보는 신뢰하지 않는다(검증 출처는 kapi 응답뿐).
- DB user upsert: 카카오 고유 id 기준. 최초면 생성, 기존이면 조회. (기존 `UserMirror`/
  `UserIdentityMirror` 스키마·ORM 관례를 따를 것 — 위 Context 참고.)

### R3. 모바일/웹 철저 분리
- **엔드포인트 분리**: 모바일은 `POST /auth/kakao/mobile`, 웹은 기존 웹 경로(`/auth/callback/kakao`)와
  별개로 유지. 공통 로직은 use_case로 추출하되 진입 경로는 나눈다.
- **Redis namespace 분리**:
  - 모바일: `auth:refresh:mobile:{userId}`
  - 웹: `auth:refresh:web:{userId}` (기존 `auth:refresh:{jti}` 스킴과 공존 방식은
    구현 시 결정 — 웹 기존 동작 회귀 금지가 최우선)
- **상호 무영향**: 모바일 로그아웃/토큰 폐기가 웹 세션에 영향 없어야 하고 그 반대도 성립.
  한 유저가 모바일·웹 동시 로그인 가능.
- refresh token 회전(rotation) 시 해당 namespace만 갱신.

### R4. Redis 저장 (RDB "컬럼"이 아니라 key namespace로 구현)
- 모바일 refresh token은 위 namespace key에 저장, TTL = refresh token 만료와 동일.
- Redis 접근은 hexagonal 포트/어댑터로 감싼다(예: `TokenStorePort` ← `RedisMobileTokenAdapter`).
  interactor는 포트에만 의존.
- 로그아웃 시 해당 key 삭제, refresh 시 검증 후 회전.

### R5. 레이어링 / 아키텍처
- `Schema → DTO → App → VO → Entity → ORM → DB` 흐름 준수. app 포트가 adapter 스키마를
  import하지 않게(DIP) 주의 — schema→DTO 변환은 router(adapter) 계층에서.
- kapi 호출, JWT 발급, Redis 저장은 각각 별도 포트로 두고 어댑터로 주입.

## Constraints
- 새 JWT 유틸을 만들지 말고 `security.py`(`JwtAdapter`) 재사용.
- 시크릿은 기존 관례(`os.getenv`)대로 읽고 하드코딩 금지. `.env`를 커밋하지 말 것.
- 웹 로그인 기존 동작을 회귀시키지 말 것 — 특히 `RefreshTokenStore`의 기존
  `auth:refresh:{jti}` 키 스킴과 웹 콜백 플로우(`services.py:84-104`)를 건드릴 경우
  기존 소비자를 확인.
- `apps/auth`가 DDL을 소유하지 않는다는 제약을 유지 — 스키마 변경이 필요하면 viewer
  쪽 마이그레이션으로 처리.

## Out of scope
- 네이버/구글 등 타 provider(이번엔 카카오만).
- OIDC(idToken) 방식(아래 Appendix 참고 — 별도 결정).
- 클라이언트(susu) UI/화면 플로우 — [susu 쪽 문서](../../susu/_docs/flutter-kakao-oauth-harness.md) 참고.

## Verification Gates (백엔드 담당분)
1. **G2 검증**: 유효 access token → user upsert + JWT 발급 성공 / 무효 토큰 → 401.
   (테스트로 kapi 호출을 mock)
2. **G3 분리**: 같은 userId로 모바일·웹 각각 로그인 → Redis에 두 개의 서로 다른 key
   존재 → 모바일 로그아웃 시 모바일 key만 삭제되고 웹 key 유지(테스트로 검증).
3. **G4 레이어**: `from main import app` 부팅 정상, auth 라우트 import 무결성,
   app→adapter DIP 위반 없음(import linter 통과).
4. 기존 auth/웹 로그인 회귀 테스트 통과.

(클라 쪽 게이트 G1은 [susu 쪽 문서](../../susu/_docs/flutter-kakao-oauth-harness.md) 참고.)

## Deliverables
- 모바일 로그인 엔드포인트(`POST /auth/kakao/mobile`) + use_case + kapi 검증 포트/어댑터
  + Redis 모바일 토큰 포트/어댑터.
- 테스트: G2/G3 커버.
- 작업 로그: `_docs/WORK_LOG.md`에 요약 기록.

---

## Appendix — 선택적 개선(이번 범위 밖, 나중에 결정)
카카오 OIDC를 켜면 로그인 결과에 `idToken`(카카오 서명 JWT)이 와서, 백엔드가 **kapi 호출
없이 JWKS 공개키로 로컬 서명 검증**만으로 신원을 확정할 수 있음(카카오로의 네트워크 요청
0회). 단 claim이 제한적(sub/nickname/email 등)이라, 최초 가입 시 상세 프로필이 필요하면
그때만 `me()`를 태우는 하이브리드가 좋음. 위 R2의 kapi 검증을 idToken 검증으로 교체하는
형태 — 이 경우 기존 `KakaoOAuthAdapter`(웹, id_token+JWKS 검증)와 검증 로직을 상당 부분
공유할 수 있어 재사용성이 높아진다.
