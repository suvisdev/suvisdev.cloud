---
paths:
  - "suvisdev/shared/security/**"
  - "suvisdev/apps/**/adapter/inbound/api/**"
  - "suvis/app/api/**/route.ts"
  - "suvis/lib/*-api.ts"
  - "suvis/lib/suvis-session.ts"
---

## 인증 · 권한 규칙

이 저장소에서 **실제 무인증 취약점이 두 번 나온** 영역이다(2026-07-27 dispatch
`email`/`telegram`/`discord`·harvester, 2026-07-28 `adress` — 익명 방문자가 실제
주소록 DB에 쓰기 가능했다). 엔드포인트를 새로 만들거나 고칠 때 아래를 확인한다.

### 1. 가드는 `require_admin` 하나로 통일

- 어드민 전용 엔드포인트는 `shared/security/require_admin.py`의 가드를 쓴다.
  앱마다 따로 만들지 않는다.
  ```python
  from shared.security.require_admin import AdminPrincipal, require_admin

  @router.get("/sites")
  async def sites(_: AdminPrincipal = Depends(require_admin)) -> list[SiteSchema]:
      ...
  ```
- 이 가드가 `shared/`에 있는 이유는 앱 간 import를 피하기 위해서다
  (`.importlinter`의 shared-independence 계약). **다른 앱의 모듈을 import해서
  인증을 구현하지 않는다.**
- 동작: `Authorization: Bearer <jwt>` 없거나 형식이 틀리면 401, JWT 서명 검증
  실패도 401, `role != "admin"`이면 403.

### 2. role은 서버가 산출한 JWT claim만 믿는다

- `role`은 로그인 시 서버가 `ADMIN_EMAILS`(env, 콤마 구분) 기준으로 계산해 JWT에
  넣은 값이다(`viewer/.../redis_session_store_adapter.py`의 `_resolve_role`).
- **클라이언트가 보내는 어떤 값도 권한 판단에 쓰지 않는다.** 프론트 세션 타입
  (`suvis/lib/suvis-session.ts`)에도 `role?: "admin" | "user"`가 있지만 이건
  localStorage에 있는 **표시용**이다 — 메뉴 노출 제어에만 쓰고, 접근 통제 근거로
  삼지 않는다. 실제 차단은 항상 백엔드 `require_admin`이 한다.
- `JWT_SECRET`은 `suvisdev/.env`에서 읽는다. 하드코딩·기본값 금지.

### 3. 토큰은 3계층 전부 전달해야 한다

프론트에 프록시 라우트가 있으면 **클라이언트 → `route.ts` → 백엔드** 세 곳 모두
토큰을 넘겨야 한다. 한 곳만 빠져도 백엔드에서 401이 나고, 원인 찾기가 오래 걸린다.

```ts
// 1) 클라이언트: lib/*-api.ts — 토큰 없으면 헤더를 아예 넣지 않는다(빈 문자열 금지)
const token = getSuvisSession()?.token
headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }

// 2) 프록시: app/api/**/route.ts — 받은 헤더를 그대로 백엔드로 넘긴다
const auth = req.headers.get("authorization")
await backendFetch(path, { headers: auth ? { Authorization: auth } : {} })
```

### 4. 무인증으로 두는 경우는 근거를 주석에 남긴다

- 현재 의도적으로 열려 있는 곳: dispatch `receive`의 **POST**(외부 시스템 인입
  경로). 같은 라우터의 GET·DELETE는 `require_admin`으로 막혀 있다.
- 새로 무인증 엔드포인트를 만들 땐 왜 열어두는지, 무엇이 들어올 수 있는지 주석에
  적는다. 근거 없이 열린 엔드포인트는 취약점으로 간주한다.
- 공개 데모 페이지가 인증이 걸린 엔드포인트를 호출하고 있지 않은지 확인한다
  (`suvis/app/mail/contacts`가 `adress`에 가드를 걸면서 401만 받게 된 상태 —
  미결 백로그).

### 5. 소유권 검증 (IDOR)

- 리소스 ID만으로 갱신·삭제하지 않는다. 요청자와 리소스 소유자가 같은지 확인한다.
- 미해결 사례: `mova/.../market_picks_router.py`의 `PATCH /{pick_id}/feedback`은
  `pick_id`만으로 갱신한다(코드에 TODO 주석 있음). **이 패턴을 새 코드에 복사하지
  않는다.**

### 6. 민감 정보 노출

- 에러 응답을 UI에 그대로 흘리지 않는다. 프론트는 `safeApiErrorMessage`를 거쳐
  짧은 문장으로만 만든다(원시 payload·비밀번호 필드·객체 전체 `JSON.stringify` 금지).
- 서버 전용 키에 `NEXT_PUBLIC_` 접두사를 붙이지 않는다. 붙이면 번들에 들어가 공개된다.
- 토큰·비밀번호를 로그에 남기지 않는다.

### 7. 엔드포인트 추가·수정 시 체크리스트

1. 이 엔드포인트는 어드민 전용인가 → `require_admin` 부착
2. 프론트에서 호출하는 경로가 프록시를 거치는가 → 3계층 토큰 전달 확인
3. 리소스를 ID로 지목해 변경하는가 → 소유권 검증
4. 무인증이라면 그 근거가 주석에 있는가
5. 같은 엔드포인트를 공개 페이지도 호출하고 있지 않은가
