# cloud.suvisdev 프론트엔드 인수인계

> **대상:** Claude Code·Cursor 등 코딩 에이전트.  
> **스택:** Next.js (App Router) · TypeScript · Tailwind CSS  
> **상위 원칙:** [[CLAUDE]] — Karpathy 네 원칙 (항상 유효)

---

## A. 에이전트가 코드를 쓰기 전에 읽을 것

| 순서  | 문서                           | 용도                                       |
| --- | ---------------------------- | ---------------------------------------- |
| 1   | **본 파일** (`suvis/_docs/CLAUDE.MD`) | 프론트엔드 구조·규칙                              |
| 2   | `_docs/react-rules.md`     | React·컴포넌트 세부 규칙 (§8 null, §9 분기, §10 try/catch) |
| 3   | `suvisdev/_docs/CLAUDE.MD`         | API 계약 확인 시 (경로만, 위키링크 없음) |

**규칙 문서를 읽지 않고 관례를 추측하여 구현하지 않는다.**

---

## B. 디렉터리 구조

```text
suvis/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # 루트 레이아웃
│   ├── page.tsx                # 메인 페이지
│   ├── globals.css
│   ├── api/                    # Next.js API Routes
│   ├── login/                  # 로그인
│   ├── signup/                 # 회원가입
│   ├── contact/                # 연락처
│   ├── lesson/                 # 레슨
│   ├── titanic/                # Titanic 섹션
│   │   ├── page.tsx
│   │   ├── data-collection/    # CSV 업로드 (James)
│   │   ├── passengers/         # 승객 조회 (Walter)
│   │   └── smith-captain/      # 선장 채팅 (Smith)
│   └── mova/                   # Mova 섹션
│       ├── page.tsx
│       ├── layout.tsx
│       ├── mova.css
│       ├── login/              # Mova 로그인
│       ├── main/               # Mova 메인 대시보드
│       ├── movies/             # 영화 목록
│       └── title/              # 영화 타이틀
├── components/                 # 공용 컴포넌트
├── lib/                        # 유틸·API 클라이언트
│   ├── apps-catalog.ts         # 앱 메타데이터
│   ├── contact-profile.ts      # 연락처 프로필
│   ├── form-status.ts          # 폼 상태 유틸
│   ├── mova-api.ts             # Mova API 클라이언트
│   ├── mova-catalog.ts         # Mova 카탈로그 데이터
│   ├── mova-mock-data.ts       # Mova 목업 데이터
│   ├── mova-movies.ts          # 영화 데이터 유틸
│   ├── mova-poster.ts          # 포스터 유틸
│   ├── suvis-session.ts        # 세션 관리
│   ├── user-facing-error.ts    # 에러 처리
│   └── utils.ts                # 공용 유틸
└── types/                      # 전역 TypeScript 타입
```

---

## C. 핵심 규칙

### C.1 서버 컴포넌트 vs 클라이언트 컴포넌트

- `page.tsx`는 기본 **서버 컴포넌트** — `fetch`, `async/await` 직접 사용.
- 상태(`useState`)·이벤트(`onClick`)·훅이 필요한 경우만 `"use client"` 추가.
- 클라이언트 컴포넌트는 `_components/` 하위에 분리.

### C.2 API 호출

- 백엔드 베이스 URL: 환경변수 `NEXT_PUBLIC_API_URL`.
- 서버 컴포넌트: 직접 `fetch`.
- 클라이언트 컴포넌트: `lib/` 내 API 클라이언트 함수 경유 (직접 `fetch` 금지).
- `fetch` 옵션: `{ cache: 'no-store' }` (실시간) 또는 `{ next: { revalidate: N } }` (ISR).

### C.3 스타일

- **Tailwind CSS** 클래스만 사용 — 인라인 `style` 속성 지양.
- 전역 스타일은 `app/globals.css`에만. Mova 전용은 `app/mova/mova.css`.

### C.4 타입

- API 응답 타입은 `types/` 또는 해당 `_components/` 내 `types.ts`에 정의.
- `any` 사용 금지 — 불명확하면 `unknown` + type guard.

### C.5 null · Record (루트 `CLAUDE.md` §5 정렬)

- **고정 필드**는 `interface` / `type`으로 정의한다. `Record<string, …>`는 **동적 키**에만 쓴다 (예: `errors: Record<string, string>`).
- `Record<string, T | null>` **금지** — 값 전체에 null을 허용하지 말고, 필요한 필드만 `foo?: T` 또는 `foo: T | null`로 표시한다.
- **없음 vs null:** 필드가 아예 없을 수 있으면 `foo?: T` (키 생략). “비어 있음”이 API·UI 계약상 명시적일 때만 `foo: T | null`.
- API 클라이언트(`lib/*-api.ts`): 백엔드가 `null`을 주는 필드만 `| null`을 붙인다. 나머지 필드에 일괄 `| null`을 붙이지 않는다.
- 객체 리터럴·상태 초기값: 없는 필드는 키를 넣지 않는다. `foo: null`은 **의미가 있는 필드**(예: `FormStatus.message`)에만.
- 상세·예시: `_docs/react-rules.md` §8.

### C.6 분기 · if/else (루트 `CLAUDE.md` §6 정렬)

- **짧은 분기는 허용** — 2~3갈래·각 갈래가 짧으면 `if/else`가 최선인 경우가 많다.
- submit·이벤트 핸들러: 검증 실패는 **앞에서 return** (guard). 성공 흐름만 아래에 둔다.
- JSX: 거대한 `condition ? <A/> : <B/>` 트리 대신 **컴포넌트 분리** 또는 early return으로 `null` 반환.
- 삼항 연산자는 **한 줄 수준** 표현에만. 중첩 삼항(`a ? b : c ? d : e`) 금지.
- `switch` / 객체 맵 dispatch: 탭·모드·`status`처럼 **같은 변수의 값 집합**이 4개 이상일 때 검토.
- 상세·예시: `_docs/react-rules.md` §9.

### C.7 try · catch (루트 `CLAUDE.md` §7 정렬)

- **경계에서만:** `app/api/**/route.ts` 프록시, `lib/*-api.ts`의 `fetch` 래퍼, submit 핸들러의 **한 번**의 async 호출.
- HTTP 실패는 `res.ok` 검사 + `safeApiErrorMessage` 우선. 예외는 **네트워크·파싱** 등 `fetch` 자체가 던질 때만 `catch`.
- `catch` 안에서 `console.log`만 하고 UI는 무시하지 않는다 — `patchX({ message })` 또는 fallback 문구.
- 중첩 `try/catch` 금지 (바깥: upstream 연결, 안쪽: JSON 파싱이 필요할 때만 **한 단계**).
- 컴포넌트 전역·렌더마다 `try/catch` 두지 않는다. Error Boundary는 루트/섹션 단위 예외.
- 상세·예시: `_docs/react-rules.md` §10.

---

## D. 라우트 구조

| 라우트 | 역할 | 백엔드 API |
|--------|------|-----------|
| `/` | 메인 | — |
| `/login` | 로그인 | `POST /viewer/login/login` |
| `/signup` | 회원가입 | `POST /viewer/signup/signup` |
| `/contact` | 연락처 | — |
| `/lesson` | 레슨 | — |
| `/titanic` | Titanic 메인 | — |
| `/titanic/data-collection` | CSV 업로드 | `POST /titanic/james/...` |
| `/titanic/passengers` | 승객 조회 | `GET /titanic/walter/...` |
| `/titanic/smith-captain` | 선장 채팅 | `POST /titanic/smith/chat` |
| `/mova` | Mova 메인 | — |
| `/mova/login` | Mova 로그인 | — |
| `/mova/main` | Mova 대시보드 | `GET /mova/...` |
| `/mova/movies` | 영화 목록 | `GET /mova/movies` |
| `/mova/title` | 영화 타이틀 | `GET /mova/movies/{id}` |

---

## E. 금지·안티패턴

| ❌ 금지 | ✅ 대신 |
|--------|--------|
| 서버 컴포넌트에 `"use client"` 무분별 추가 | 필요한 최소 단위만 클라이언트 컴포넌트로 분리 |
| 클라이언트 컴포넌트에서 `fetch` 직접 호출 | `lib/` API 클라이언트 경유 |
| 하드코딩 API URL | `NEXT_PUBLIC_API_URL` 환경변수 |
| `any` 타입 | `unknown` + type guard 또는 명시적 타입 |
| `Record<string, T \| null>` | `interface` + 필드별 `?` / `\| null` |
| `if` 3단 이상 중첩 · 중첩 삼항 | guard return · 컴포넌트 분리 · `react-rules.md` §9 |
| `catch (e)` 무분별 · 중첩 `try/catch` | 경계 1겹 · `res.ok` + `safeApiErrorMessage` · `react-rules.md` §10 |
| `style={{ ... }}` 인라인 스타일 | Tailwind 클래스 |

---

## F. 관련 문서

| 문서 | 경로 |
|------|------|
| 루트 Karpathy 원칙 | (상단 [[CLAUDE]] 링크) |
| React 세부 규칙 | `react-rules.md` |
| 백엔드 API | `suvisdev/_docs/CLAUDE.MD` (경로만) |


## 다크 모드

→ 구현 명세: `darkmode_spec.md` (동일 `_docs/` 폴더)