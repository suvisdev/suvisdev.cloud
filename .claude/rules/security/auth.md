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

### 3. 토큰은 httpOnly 쿠키에 있다 — 프록시가 쿠키를 읽어 Bearer로 (2026-09-30 전환)

구 localStorage 토큰(클라가 Bearer로 실어 보내던 3계층 전달)은 **XSS로 탈취 가능**해
폐기했다. 이제 로그인은 `/api/auth/login` BFF가 access·refresh를 **httpOnly 쿠키**로 심고,
클라이언트는 토큰을 만지지 않는다.

```ts
// 1) 클라이언트: Authorization을 직접 붙이지 않는다. same-origin 프록시로 나가면 쿠키가 자동 전송된다.
await fetch("/api/backend/mova/reviews", { method: "POST", body })      // catch-all 경유
await fetch("/api/mova/chat", { method: "POST", body })                 // 개별 프록시 경유

// 2) 프록시: 쿠키의 access를 Bearer로 읽어 백엔드에 전달한다(구 pass-through 자리).
import { cookieBearer } from "@/lib/auth-bff"
const auth = await cookieBearer()   // "Bearer <access>" or undefined
await backendFetch(path, { headers: auth ? { Authorization: auth } : {} })
```

서버 헬퍼(`setAuthCookies`·`cookieBearer`·`forwardToBackend` 등)는 전부 `suvis/lib/auth-bff.ts`에
있다. 쿠키는 same-origin Next 프록시가 심는다(auth 게이트웨이는 다른 도메인이라 못 심는다).
role은 여전히 표시용(§2) — 접근 통제는 백엔드 `require_admin`이 JWT로 한다.

### 4. 무인증으로 두는 경우는 근거를 주석에 남긴다

- 현재 의도적으로 열려 있는 곳: dispatch `receive`의 **POST**(외부 시스템 인입
  경로). 같은 라우터의 GET·DELETE는 `require_admin`으로 막혀 있다.
- 새로 무인증 엔드포인트를 만들 땐 왜 열어두는지, 무엇이 들어올 수 있는지 주석에
  적는다. 근거 없이 열린 엔드포인트는 취약점으로 간주한다.
- 공개 데모 페이지가 인증이 걸린 엔드포인트를 호출하고 있지 않은지 확인한다
  (`suvis/app/mail/contacts`가 이 상태로 한동안 방치됐다가 2026-08-27
  `app/mail/layout.tsx`의 `AdminAuthGate`로 정리됨 — 백엔드를 잠그면 그걸
  호출하는 페이지의 노출·토큰 전달까지 같은 작업에서 맞춘다).

### 5. 소유권 검증 (IDOR)

- 리소스 ID만으로 갱신·삭제하지 않는다. 요청자와 리소스 소유자가 같은지 확인한다.
- **`user_id`를 경로·바디로 받는 엔드포인트는 그 값을 신뢰하지 않는다.** 신원은
  토큰에서만 온다. 2026-08-07 전수 조사에서 이 한 가지 패턴으로 5건이 나왔다 —
  `/mova/mypage/{user_id}`, `/viewer/profile/{user_id}`(이메일 노출),
  `/mova/watchlist/*`(읽기+**쓰기**), `/mova/picks/{pick_id}/feedback`,
  `/mova/chat`(바디 `user_id`). 전부 수정됐다.
- 참고 구현 두 가지:
  - **라우터에서 대조**(리소스 조회가 이미 있을 때) — `market_reviews_router.py`
    `PATCH /{review_id}`: `get_by_id` → 404 → 소유자 불일치면 403.
  - **쿼리에 소유권을 함께 거는 방식**(조회를 한 번으로 줄일 때) —
    `market_picks_pg_repository.update_feedback()`: `WHERE id=? AND user_id=?`.
    이때 "없음"과 "남의 것"을 **구분해 알려주지 않는다**(id를 훑어 존재를
    캐내는 것 방지).
- 로그인이 선택인 엔드포인트는 `shared/security/require_user.py`의
  `optional_user`를 쓴다 — 토큰이 있으면 신원을 주고 없으면 `None`(익명).
  **토큰이 붙었는데 무효면 익명으로 강등하지 말고 401**을 낸다(개인화가 왜
  끊겼는지 사용자가 알 수 있어야 한다). `/mova/chat`이 이 패턴이다.

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
