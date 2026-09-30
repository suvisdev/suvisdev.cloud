---
paths:
  - "suvis/lib/*-api.ts"
  - "suvis/app/api/**/route.ts"
---

## API 클라이언트 · 라우트 핸들러 규칙

`suvis/`가 백엔드(FastAPI)와 통신하는 두 경로 — `lib/*-api.ts`(클라이언트에서
쓰는 API 함수)와 `app/api/**/route.ts`(Next.js 라우트 핸들러/프록시) — 의 현행
관례다.

> 어느 계층에서 무엇을 호출하는지(서버 컴포넌트는 직접 `fetch`, 클라이언트
> 컴포넌트는 `lib/` 경유)는 `suvis/CLAUDE.md` C.2가 기준이다. 여기서는
> **그 함수를 어떻게 쓰는지**만 다룬다.

### 1. 베이스 URL

- 백엔드 주소는 `process.env.NEXT_PUBLIC_API_URL`에서 읽고, 로컬 기본값을 뒤에
  둔다. URL을 하드코딩하지 않는다.
  ```ts
  const API_BASE =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
    "http://127.0.0.1:8000"
  ```
- 서버 전용 키(`GEMINI_API_KEY` 등)는 `NEXT_PUBLIC_` 접두사를 붙이지 않는다.
  라우트 핸들러 안에서만 읽고, 없으면 503으로 응답한다.

### 2. fetch 래퍼는 파일당 하나, 제네릭으로

- `lib/*-api.ts`마다 모듈 전용 `fetch` 래퍼를 하나 두고 모든 함수가 그것을
  경유한다. 개별 함수에서 `fetch`를 직접 부르지 않는다.
  ```ts
  async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const token = getSuvisSession()?.token
    const res = await fetch(`${API_BASE}/viewer/admin/agents${path}`, {
      ...init,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
    })
    const data = (await res.json()) as T & ApiErrorBody
    if (!res.ok) {
      throw new Error(safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status))
    }
    return data
  }
  ```
- 공개 함수는 이 래퍼를 감싸는 얇은 한 줄로 유지한다:
  ```ts
  export function listAgents(): Promise<AgentSummary[]> {
    return adminFetch<AgentSummary[]>("")
  }
  ```
- 에러 본문 타입은 `type ApiErrorBody = { detail?: string | unknown }`으로 두고
  응답 타입과 교차시킨다.

### 3. 인증 — httpOnly 쿠키 BFF (2026-09-30 전환)

**토큰은 localStorage에 없다.** 로그인 시 `/api/auth/login`·`/api/auth/signup` BFF가
access·refresh를 **httpOnly 쿠키**(`sv_access`·`sv_refresh`)로 심고, 클라이언트엔
사용자 정보(id·username)만 준다. 구 `getSuvisSession()?.token` + `authHeader()`는
제거됐다(XSS 탈취 방지).

- **클라이언트는 Authorization 헤더를 직접 붙이지 않는다.** 인증 호출은 same-origin
  프록시로 나가고(쿠키가 자동 전송된다), 프록시가 쿠키를 읽어 Bearer로 바꿔 백엔드에 전달한다.
- **직결이던 호출**(admin·mova-api·games·gildle·vision·titanic 등)은 catch-all
  **`/api/backend/[...path]`**를 쓴다 — 클라가 `/api/backend/mova/...`를 부르면
  `lib/auth-bff.ts`의 `forwardToBackend`가 쿠키→Bearer + 401 시 리프레시까지 한다.
- **경로 변형·로직이 있는 개별 프록시**(`/api/mova/*`·`/api/viewer/*`·`/api/dispatch/*` 등)는
  `cookieBearer()`로 쿠키의 access를 Bearer로 읽는다(구 `request.headers.get("authorization")`
  pass-through 자리). 서버 헬퍼는 전부 `lib/auth-bff.ts`에 있다.
- **로그아웃**은 `logoutSession()`(→ `/api/auth/logout`)이 refresh를 revoke하고 쿠키를 지운다 —
  `clearSuvisSession()`(localStorage만)으로 끝내지 않는다.
- 백엔드 게이트웨이는 그대로다(access+refresh 발급·`/auth/refresh`·`/auth/logout` 재사용). 쿠키
  세팅은 백엔드가 아니라 **same-origin Next 프록시**가 한다(게이트웨이는 다른 도메인이라 쿠키를 못 심는다).
- access TTL은 현재 7일 유지 — 쿠키도 7일이라 리프레시 없이 UX 동일. 짧은 TTL+리프레시 상시화는
  후속(리프레시 인프라·catch-all 자동회전은 준비돼 있음).

### 4. 에러 처리

- HTTP 실패는 예외가 아니라 `res.ok` 검사로 판정한다.
- 사용자에게 보여줄 문구는 반드시 `safeApiErrorMessage(detail, fallback, status)`를
  거친다. 백엔드 `detail`(문자열·배열·객체 어느 것이든 올 수 있음)을
  `JSON.stringify`로 그대로 노출하지 않는다.
- 커스텀 에러 클래스는 두지 않는다 — `throw new Error(safeApiErrorMessage(...))`가
  현행 관례다.
- `try/catch`는 경계 한 겹만. 상세 기준은 `suvis/CLAUDE.md` C.7 및
  `react-rules.md` §10.

### 5. 라우트 핸들러(`app/api/**/route.ts`)

- 입력 검증은 **앞에서 guard return**으로 처리하고 각각 적절한 상태 코드를 준다.
  본문 파싱 실패 400, 필수 값 누락 400, 서버 키 미설정 503, 업스트림 실패 502.
  ```ts
  let body: { messages?: ChatMessage[] }
  try {
    body = (await request.json()) as { messages?: ChatMessage[] }
  } catch {
    return NextResponse.json({ error: "잘못된 요청 본문입니다." }, { status: 400 })
  }
  ```
- 응답은 `NextResponse.json(...)`으로 통일하고, 에러 응답 본문은 `{ error: string }`
  형태를 유지한다.
- 업스트림 호출만 `try/catch`로 감싸고 메시지는 좁혀서 꺼낸다:
  ```ts
  const message = e instanceof Error ? e.message : "답변을 가져오지 못했습니다."
  ```
- 다른 파일의 핸들러를 재노출할 때는 재구현하지 말고 그대로 re-export한다:
  `export { POST } from "@/components/api/chat/route"`
