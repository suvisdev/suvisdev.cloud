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

### 3. 인증 — 세션 Bearer 전달

- 인증이 필요한 엔드포인트는 `getSuvisSession()?.token`을 `Authorization: Bearer`로
  실어 보낸다. 토큰이 없으면 헤더를 **아예 넣지 않는다**(빈 문자열 금지).
- 프록시 라우트를 거치는 경우 **클라이언트 → `route.ts` → 백엔드** 3계층 모두
  토큰을 전달해야 한다. 한 곳이라도 빠지면 백엔드 `require_admin`에서 401이 난다.

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
