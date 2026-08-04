# cloud.suvisdev 프론트엔드 인수인계

> **대상:** Claude Code·Cursor 등 코딩 에이전트.  
> **스택:** Next.js (App Router) · TypeScript · Tailwind CSS · shadcn/ui  
> **상위 원칙:** [[CLAUDE]] — Karpathy 네 원칙 (항상 유효)

---

## A. 에이전트가 코드를 쓰기 전에 읽을 것

| 순서 | 문서                      | 용도                                                       |
| ---- | ------------------------- | ---------------------------------------------------------- |
| 1    | **본 파일** (`suvis/CLAUDE.md`) | 프론트엔드 구조·규칙                                        |
| 2    | `_docs/react-rules.md`    | React·컴포넌트 세부 규칙 (§8 null, §9 분기, §10 try/catch)  |
| 3    | `_docs/DESIGN.md`         | 스타일링(Tailwind+shadcn 토큰) 정책·mova 서브앱 토큰 규칙   |
| 4    | `suvisdev/CLAUDE.md`      | API 계약 확인 시 (경로만, 위키링크 없음)                    |

**규칙 문서를 읽지 않고 관례를 추측하여 구현하지 않는다.**

---

## B. 디렉터리 구조

```text
suvis/
├── app/                         # Next.js App Router
│   ├── layout.tsx               # 루트 레이아웃
│   ├── page.tsx                 # 메인 페이지
│   ├── globals.css              # 전역 스타일 (shadcn 토큰 + mova 토큰 @theme 등록)
│   ├── api/                     # Next.js API Routes (백엔드 프록시)
│   │   ├── auth/                # 로그인·회원가입·oauth
│   │   ├── analytics/           # 방문자 통계
│   │   ├── chat/, gemini/       # AI 챗 프록시
│   │   ├── dispatch/            # 이메일·텔레그램·디스코드·주소록 발송
│   │   ├── harvester/           # 크롤링(sites/policies/scrape/crawl)
│   │   ├── mova/                # 영화 추천 전체 API
│   │   └── viewer/              # 프로필
│   ├── admin/                   # 어드민 대시보드(홈/사용자/앱관리/통계/캘린더/설정/dispatch/harvester)
│   ├── apps/                    # 앱 카탈로그
│   ├── contact/                 # 연락처
│   ├── devlog/                  # 개발 일지
│   ├── dispatch/                # 발송 데모(공개)
│   ├── langchain/chat/          # LangChain 챗 데모
│   ├── lesson/                  # 레슨
│   ├── login/, signup/          # 인증
│   ├── mail/                    # 메일·연락처 공개 데모 (mail/contacts는 adress 백엔드 인증 필요 — 401 이슈 있음, 아래 D 참고)
│   ├── mova/                    # Mova(영화 추천) 섹션 — 자체 브랜드 토큰(mova.css), 상세는 `_docs/DESIGN.md`
│   │   ├── page.tsx, layout.tsx, mova.css
│   │   ├── login/, main/, movies/, collections/, rankings/, title/, mypage/
│   ├── mypage/                  # 마이페이지
│   ├── oauth/                   # OAuth 콜백·동의
│   ├── privacy/, terms/         # 약관
│   ├── soccer/chat/             # 축구 챗 데모
│   ├── telegram/                # 텔레그램 데모
│   ├── test-auth-login/         # 인증 플로우 테스트 페이지
│   ├── titanic/                 # Titanic 섹션
│   │   ├── page.tsx
│   │   ├── data-collection/     # CSV 업로드 (James)
│   │   ├── passengers/          # 승객 조회 (Walter)
│   │   └── smith-captain/       # 선장 채팅 (Smith)
│   └── vision/                  # 비전(이미지 업로드·object-detection)
├── components/
│   ├── ui/                      # shadcn/ui 컴포넌트(설치돼 있는 전체 목록은 `components.json` + `ls components/ui`)
│   ├── admin/, mova/, home/, mail/ …  # 도메인별 컴포넌트
├── lib/                         # 유틸·API 클라이언트 (`lib/*-api.ts` 패턴은 `.claude/rules/api-standards.md`)
│   ├── admin-*-api.ts           # 어드민 대시보드 API 클라이언트 6종(agents/apps/calendar/dashboard/settings/stats/users)
│   ├── apps-catalog.ts          # 앱 메타데이터
│   ├── backend-client.ts        # 공용 fetch 베이스
│   ├── contact-profile.ts       # 연락처 프로필
│   ├── devlog.ts                # 개발 일지 데이터
│   ├── form-status.ts           # 폼 상태 유틸(`react-rules.md` §2)
│   ├── harvester-api.ts         # 크롤링 API 클라이언트
│   ├── mova-api.ts, mova-catalog.ts, mova-mock-data.ts, mova-movies.ts,
│   │   mova-poster.ts, mova-chat-suggestions.ts, load-mova-title.ts  # Mova 관련
│   ├── oauth-api.ts, profile-api.ts, suvis-session.ts  # 인증·세션
│   ├── user-facing-error.ts     # `safeApiErrorMessage`
│   ├── visitor-analytics-api.ts, visitor-id.ts  # 방문자 통계
│   └── utils.ts                 # `cn()` 등 공용 유틸
└── components.json              # shadcn/ui 설정(style=new-york, baseColor=neutral)
```

> **`types/` 디렉터리는 없다.** API 응답 타입은 쓰는 곳 옆(`lib/*-api.ts` 안,
> 또는 해당 컴포넌트 파일에 `export type`)에 둔다 — `.claude/rules/typescript.md`
> §3. 전역 `types/`를 새로 만들지 않는다.

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
- 프록시(`app/api/**/route.ts`)와 인증 3계층 전달 규칙은 `.claude/rules/api-standards.md`.

### C.3 스타일 — Tailwind + shadcn/ui 토큰 하나로 통일

- 색상은 **shadcn 토큰**(`bg-background`, `text-foreground`, `bg-primary`,
  `border-border` 등)을 쓴다. 하드코딩 색상·새 전역 CSS 변수를 만들지 않는다.
- `app/mova/**`·`components/mova/**` 안에서는 `bg-mova-*`/`text-mova-*`/
  `border-mova-*` **명명 유틸리티**를 쓴다(`var(--mova-*)` 임의값 문법을 새로
  쓰지 않는다 — 이미 `app/globals.css`의 `@theme inline`에 등록돼 있다).
- Tailwind로 표현 안 되는 CSS(스크롤바, `offset-path`, `@keyframes`, 가상 요소
  그라디언트)는 인라인 스타일이 아니라 스코프의 CSS 파일에 raw CSS로 둔다
  (`app/globals.css` 전역, `app/mova/mova.css` mova 전용).
- 인라인 `style={{}}`는 런타임에만 정해지는 값(진행률 %, 데이터 인덱스별 색상,
  `transform`)에만 쓴다.
- shadcn 컴포넌트가 없으면 `pnpm dlx shadcn@latest add <컴포넌트>`로 받는다 —
  직접 처음부터 만들지 않는다.
- 전체 정책·근거·새 브랜드 색 추가 절차: `_docs/DESIGN.md`.

### C.4 타입

- API 응답 타입은 해당 `lib/*-api.ts` 또는 컴포넌트 파일에 `export type`으로
  정의한다(쓰는 곳 옆). 전역 `types/` 디렉터리를 새로 만들지 않는다.
- `any` 사용 금지 — 불명확하면 `unknown` + type guard.
- 상세: `.claude/rules/typescript.md`.

### C.5 null · Record (루트 `CLAUDE.md` §5 정렬)

- **고정 필드**는 `interface` / `type`으로 정의한다. `Record<string, …>`는 **동적 키**에만 쓴다 (예: `errors: Record<string, string>`).
- `Record<string, T | null>` **금지** — 값 전체에 null을 허용하지 말고, 필요한 필드만 `foo?: T` 또는 `foo: T | null`로 표시한다.
- **없음 vs null:** 필드가 아예 없을 수 있으면 `foo?: T` (키 생략). "비어 있음"이 API·UI 계약상 명시적일 때만 `foo: T | null`.
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

전체 39개 라우트 그룹 중 백엔드 연동이 있는 주요 라우트만 정리한다. 목록에
없는 라우트(로그인·약관 등 정적 페이지)는 백엔드 호출이 없거나 `app/api/**`
프록시를 그대로 따라가면 된다.

| 라우트 | 역할 | 백엔드 연동 |
|--------|------|-----------|
| `/` | 메인 | — |
| `/login`, `/signup` | 로그인·회원가입 | `POST /viewer/login/login`, `POST /viewer/signup/signup` |
| `/oauth/callback`, `/oauth/consent` | OAuth 콜백·동의 | `apps/auth` |
| `/contact`, `/lesson`, `/apps`, `/devlog` | 정적/카탈로그 페이지 | — |
| `/mail`, `/mail/contacts` | 연락처 공개 데모 | `dispatch` adress(현재 `require_admin` 가드로 공개 페이지 401 — 미결, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 참고) |
| `/dispatch`, `/telegram`, `/soccer/chat`, `/langchain/chat` | 발송·챗 데모 | `dispatch`, `execsuite` 등 |
| `/titanic` | Titanic 메인 | — |
| `/titanic/data-collection` | CSV 업로드 | `POST /titanic/james/...` |
| `/titanic/passengers` | 승객 조회 | `GET /titanic/walter/...` |
| `/titanic/smith-captain` | 선장 채팅 | `POST /titanic/smith/chat` |
| `/vision`, `/vision/object-detection` | 비전 업로드·객체 검출 | `apps/ontology` vision |
| `/mova/**` | Mova(영화 추천) 전체 — `main`/`movies`/`collections`/`rankings`/`title`/`mypage`/`login` | `apps/mova` 전체(`lib/mova-api.ts`) |
| `/mypage` | 마이페이지 | `viewer/profile` |
| `/admin/**` | 어드민 대시보드(홈/사용자/앱관리/통계/캘린더/설정/dispatch/harvester) | `require_admin` 가드, `lib/admin-*-api.ts` |
| `/test-auth-login` | 인증 플로우 수동 테스트 페이지 | `apps/auth` |

---

## E. 금지·안티패턴

| ❌ 금지 | ✅ 대신 |
|--------|--------|
| 서버 컴포넌트에 `"use client"` 무분별 추가 | 필요한 최소 단위만 클라이언트 컴포넌트로 분리 |
| 클라이언트 컴포넌트에서 `fetch` 직접 호출 | `lib/` API 클라이언트 경유 |
| 하드코딩 API URL | `NEXT_PUBLIC_API_URL` 환경변수 |
| `any` 타입 | `unknown` + type guard 또는 명시적 타입 |
| `Record<string, T \| null>` | `interface` + 필드별 `?` / `\| null` |
| 새 전역 `types/` 디렉터리 생성 | 쓰는 곳 옆에 `export type` |
| 색상 하드코딩·새 전역 CSS 변수 | shadcn 토큰(`bg-primary` 등) · mova는 `bg-mova-*` |
| mova에서 `var(--mova-*)` 임의값 문법 새로 사용 | `bg-mova-*`/`text-mova-*` 명명 유틸리티(`_docs/DESIGN.md`) |
| `if` 3단 이상 중첩 · 중첩 삼항 | guard return · 컴포넌트 분리 · `react-rules.md` §9 |
| `catch (e)` 무분별 · 중첩 `try/catch` | 경계 1겹 · `res.ok` + `safeApiErrorMessage` · `react-rules.md` §10 |
| `style={{ ... }}` 인라인 스타일(정적 값) | Tailwind 클래스 |

---

## F. 관련 문서

| 문서 | 경로 |
|------|------|
| 루트 Karpathy 원칙 | (상단 [[CLAUDE]] 링크) |
| React 세부 규칙 | `_docs/react-rules.md` |
| 스타일링(Tailwind+shadcn 토큰) 정책 | `_docs/DESIGN.md` |
| 다크 모드 구현 명세 | `_docs/darkmode_spec.md` |
| API 클라이언트·라우트 핸들러 규칙 | `.claude/rules/api-standards.md` |
| TypeScript 규칙 | `.claude/rules/typescript.md` |
| 백엔드 API | `suvisdev/CLAUDE.md` (경로만) |
