---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

## TypeScript 규칙

`suvis/`(Next.js App Router · TypeScript 5.7 · React 19)에서 실제로 쓰고 있는
패턴을 유지하기 위한 규칙이다. 아래 항목은 전부 현행 코드에서 측정한 관례이며,
새 코드는 이 관례를 따른다.

> React·컴포넌트 세부 규칙은 `suvis/_docs/react-rules.md`, 프론트 전반 구조는
> `suvis/_docs/CLAUDE.MD`를 따른다. 여기서는 **타입 언어 차원의 규칙**만 다룬다.

### 1. strict mode 필수

- `suvis/tsconfig.json`의 `strict: true`를 끄거나 개별 옵션으로 완화하지 않는다.
- 검증은 `pnpm type-check`(`tsc --noEmit`). 타입 에러를 남긴 채 커밋하지 않는다.
- 경로 별칭은 `@/*` 하나만 쓴다(상대경로 `../../..` 금지).

### 2. any 금지 — unknown + 좁히기

- `any`는 쓰지 않는다(현행 코드 사용 0건). 타입이 불명확하면 `unknown`으로 받고
  좁힌다.
- 외부 경계(에러 `detail`, JSON 본문)는 `unknown`으로 선언한 뒤 `typeof` ·
  `Array.isArray` · `in` 으로 검사한다. `lib/user-facing-error.ts`의
  `safeApiErrorMessage(detail: unknown, ...)`이 기준 예시다.
- `catch`는 타입을 붙이지 않고(`catch (e)`), 꺼내 쓸 때 좁힌다:
  `const message = e instanceof Error ? e.message : "기본 문구"`.
- 배열을 좁힐 때는 타입 술어를 쓴다:
  `.filter((r): r is MovaRecommendation => r !== null)`.

### 3. 인터페이스보다 타입 별칭 선호

- 새 타입은 `type`으로 정의한다(현행 `type` 167건 : `interface` 4건).
- `interface`는 `components/ui/**`처럼 **shadcn/ui에서 생성된 파일**을 수정할 때만
  기존 형태를 유지하는 용도로 남긴다. 직접 작성하는 코드에는 쓰지 않는다.
- 타입 확장은 `extends`가 아니라 교차 타입으로:
  `type AgentDetail = AgentSummary & { model: string }`.
- 선언 위치는 **쓰는 곳 옆**이다. API 응답 타입은 해당 `lib/*-api.ts`에,
  컴포넌트 전용 타입은 그 컴포넌트 파일에 `export type`으로 둔다
  (전역 `types/` 디렉터리는 현재 쓰지 않는다).

### 4. enum 금지 — 문자열 리터럴 유니온

- `enum`은 쓰지 않는다(현행 사용 0건). 값 집합은 리터럴 유니온으로 표현한다.
  ```ts
  type OAuthProvider = "google" | "naver" | "kakao"
  type Step = "exchanging" | "calling-whoami" | "done" | "error"
  ```
- 그 유니온에 대응하는 표시 문자열·스타일 맵은 `Record<유니온, T>`로 만들어
  누락을 컴파일러가 잡게 한다: `const PERIOD_LABEL: Record<StatsPeriod, string>`.

### 5. 컴포넌트·함수 시그니처

- `React.FC`를 쓰지 않는다(현행 사용 0건). 일반 함수 선언에 props 타입을 직접
  붙인다.
- props가 3개 이상이거나 재사용되면 이름 있는 `XxxProps` 타입으로 분리한다.
  1~2개면 인라인으로 둔다.
  ```ts
  type MovaHeroBannerProps = { title: string; imageUrl: string | null }
  export function MovaHeroBanner({ title, imageUrl }: MovaHeroBannerProps) {}

  export default function AdminLayout({ children }: { children: ReactNode }) {}
  ```
- 공통 로직은 제네릭으로 한 번만 쓴다 — `async function adminFetch<T>(path: string,
  init?: RequestInit): Promise<T>`, `patchState<T extends object>(setter, patch: Partial<T>)`.
- 내보내는 async 함수는 반환 타입을 명시한다: `Promise<AgentSummary[]>`.

### 6. null · 선택 필드

- `null`을 기본으로 쓰고(`| null` 106건 : `| undefined` 20건), 값이 없을 수 있는
  자리는 `??`로 대체값을 준다.
- 필드가 아예 없을 수 있으면 `foo?: T`, "비어 있음"이 API·UI 계약상 명시적일 때만
  `foo: T | null`. 상세 기준은 `suvis/_docs/CLAUDE.MD` C.5 및
  `react-rules.md` §8을 따른다.
- `Record<string, T | null>` 금지 — `Record`는 **동적 키**에만 쓴다.

### 7. 타입 단언은 경계에서만

- `as`는 `fetch` 응답 파싱 같은 **외부 입력 경계**에서만 쓴다:
  `const data = (await res.json()) as T & ApiErrorBody`.
  이미 타입이 있는 값을 다른 타입으로 우회 변환하는 용도로 쓰지 않는다.
- non-null 단언(`!`)은 쓰지 않는다(현행 1건뿐). 좁히기나 기본값으로 해결한다.
- `as any` · `@ts-ignore` · `@ts-expect-error`는 금지한다.
