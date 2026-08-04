# suvis 스타일링 하네스 — Tailwind CSS + shadcn/ui 통일

## 목적

`suvis/`의 스타일링을 **Tailwind CSS + shadcn/ui 토큰 체계 하나로 통일**한다.
2026-08-04 실측 기준으로 병렬 스타일 시스템 두 곳(죽은 CSS 파일 하나, mova 서브앱
전용 CSS 변수 시스템 하나)이 있었고, 이 문서는 그 통일 작업의 실행 기록 겸
앞으로 새 화면을 추가할 때 따를 규칙이다.

---

## 원래 상태 (실측)

| 파일 | 상태 |
|------|------|
| `app/globals.css` | 실제 사용 중 — shadcn 토큰(`:root`/`.dark` CSS 변수 → `@theme inline`), `app/layout.tsx`가 import |
| `styles/globals.css` | **죽은 파일** — 아무 데서도 import 안 됨(초기 스캐폴딩 잔재로 추정) |
| `app/mova/mova.css` | mova 서브앱(`app/mova/**`, `components/mova/**`) 전용. `.mova-app`/`html:not(.dark) .mova-app` 스코프에 `--mova-bg`·`--mova-surface`·`--mova-accent` 등 **자체 색상 변수**를 정의 — shadcn 토큰과 별개 체계 |
| tsx 27개 파일 | mova 색상을 `text-[var(--mova-text)]`, `bg-[var(--mova-surface)]` 같은 **Tailwind 임의값(arbitrary value)** 문법으로 357곳에서 참조 |

`components.json`(shadcn 설정: style=`new-york`, baseColor=`neutral`,
cssVariables=`true`)과 `app/globals.css`의 `@theme inline` 매핑 자체는 이미
표준 shadcn 패턴이었다 — 문제는 mova 서브앱이 **같은 메커니즘을 안 쓰고 자체
CSS 변수 + 임의값 문법으로 우회**하고 있었다는 점이다.

---

## 통일 방침: "색은 토큰화, 비-색상 CSS는 그대로"

Tailwind 유틸리티로 표현 안 되는 것들(스크롤바 `::-webkit-scrollbar-thumb`,
`offset-path` 모션, `::view-transition-old/new`, `@keyframes`, 가상 요소
그라디언트 페이드)까지 억지로 인라인 클래스로 밀어 넣지 않는다. `app/globals.css`
자체도 `.auth-dialog-shell` 오버라이드·`@keyframes titanic-bubble-rise`를
raw CSS로 갖고 있다 — **이런 것들은 CSS 파일에 남기는 게 이 저장소의 기존
관례**이고 Tailwind 공식 권장 방식이기도 하다. "통일"의 실질 대상은 **색상
토큰의 노출 방식**이다:

- **바뀐 것**: mova 색상 변수를 shadcn과 똑같은 경로(`@theme inline`)로 등록해서
  `text-mova-text`, `bg-mova-surface` 같은 **명명된 Tailwind 유틸리티**로 쓰게
  했다. `bg-primary`/`text-muted-foreground`와 동일한 패턴이 됐다.
- **안 바뀐 것**: mova의 실제 색상 값·다크/라이트 분기·`.mova-app` 스코프는
  전혀 건드리지 않았다. `mova-logo.tsx`의 `shadow-[0_0_12px_var(--mova-accent-soft)]`,
  `mova-ai-chat-bar.tsx`의 그라디언트 배경, `mova-intro.tsx`의 SVG `stroke`
  속성처럼 **여러 값이 합성된 임의값**은 그대로 뒀다 — 이런 건 애초에 named
  utility로 못 바꾼다(값 하나가 아니라 CSS 표현식 전체이므로).

### `@theme inline` 등록 (`app/globals.css`)

```css
/* mova(app/mova/mova.css) 전용 토큰 — 값은 .mova-app 스코프에서 정의(다크/라이트
   시네마 브랜딩). shadcn 토큰과 같은 @theme inline 경로로만 노출해 bg-mova-*
   형태의 명명 유틸리티를 쓰게 한다(전역 :root 색상이 아니므로 .mova-app
   밖에서는 값이 없다). */
--color-mova-bg: var(--mova-bg);
--color-mova-surface: var(--mova-surface);
--color-mova-surface-2: var(--mova-surface-2);
--color-mova-border: var(--mova-border);
--color-mova-accent: var(--mova-accent);
--color-mova-accent-soft: var(--mova-accent-soft);
--color-mova-accent-bright: var(--mova-accent-bright);
--color-mova-ai: var(--mova-ai);
--color-mova-muted: var(--mova-muted);
--color-mova-text: var(--mova-text);
```

`@theme inline`은 값이 아니라 "이 이름의 유틸리티는 이 CSS 변수를 쓴다"는
매핑만 등록한다. 실제 값은 여전히 `app/mova/mova.css`의 `.mova-app`(다크)/
`html:not(.dark) .mova-app`(라이트) 스코프에서 정의되므로, `bg-mova-surface`
클래스는 **`app/mova/layout.tsx`의 `<div className="mova-app ...">` 안에서만**
의도한 색으로 렌더된다(밖에서 쓰면 변수가 비어 있다) — 이 스코프 제약은 기존과
동일하고, 이 작업으로 바뀐 게 없다.

### tsx 치환

357곳 중 354곳을 기계적으로 치환했다: `\[var\(--mova-([a-z0-9-]+)\)\]` →
`mova-$1` (예: `text-[var(--mova-text)]` → `text-mova-text`,
`hover:bg-[var(--mova-surface-2)]` → `hover:bg-mova-surface-2`,
`border-[var(--mova-accent)]/40` → `border-mova-accent/40`). opacity modifier
(`/40` 등)와 `hover:`/`focus:`/`group-hover:`/`focus-within:` 변형, gradient
stop(`from-`/`via-`/`to-`)까지 전부 named token 문법으로 동일하게 동작한다
(Tailwind가 커스텀 테마 컬러에도 `color-mix()` 기반 opacity modifier를 그대로
적용하므로 — 빌드 산출물에서 `.bg-mova-surface\/90{background-color:color-mix(in
oklab, var(--mova-surface) 90%, transparent)}` 확인함).

**시각적으로 아무것도 안 바뀐다** — `.bg-mova-surface{background-color:var(--mova-surface)}`
로 컴파일되는 것은 치환 전 `bg-[var(--mova-surface)]`가 컴파일되던 결과와
바이트 단위로 동일하다. 순수 문법 치환이다.

---

## 정리한 것

- `styles/globals.css` 삭제 — 미사용 죽은 파일.

---

## 새 화면·컴포넌트를 만들 때 규칙

1. **shadcn 토큰을 우선 쓴다** — `bg-background`, `text-foreground`,
   `bg-primary`, `border-border` 등. 색을 하드코딩하거나 새 CSS 변수를 만들지
   않는다.
2. **mova 서브앱**(`app/mova/**`, `components/mova/**`) 안에서는 `bg-mova-*`/
   `text-mova-*`/`border-mova-*` named 유틸리티를 쓴다. `var(--mova-*)` 임의값
   문법을 새로 쓰지 않는다 — 이미 named token이 있으므로.
3. **새 브랜드 색이 필요하면** `app/mova/mova.css`의 `.mova-app`/
   `html:not(.dark) .mova-app`에 변수를 추가하고, `app/globals.css`의
   `@theme inline`에 `--color-mova-<name>: var(--mova-<name>);` 한 줄을 같이
   추가한다 — 변수만 추가하고 `@theme inline` 등록을 빼먹으면 named 유틸리티가
   생성되지 않는다.
4. **Tailwind로 표현 안 되는 CSS**(스크롤바, `offset-path`, 가상 요소 애니메이션,
   `@keyframes`)는 인라인 스타일이나 새 CSS-in-JS 라이브러리를 끌어오지 않고
   해당 스코프의 CSS 파일(`app/globals.css` 전역, `app/mova/mova.css` mova
   전용)에 raw CSS로 둔다. 이건 회피 대상이 아니라 이 저장소의 정상 패턴이다.
5. **인라인 `style={{}}`는 런타임에만 정해지는 값**(진행률 %, 데이터 인덱스별
   색상, `transform`)에만 쓴다. 정적으로 알 수 있는 값은 Tailwind 클래스로.

---

## 검증

- `pnpm type-check` — 통과
- `pnpm build` — 통과, `app/mova/**` 전 라우트 정상 컴파일
- 빌드 산출물 CSS(`​.next/static/chunks/*.css`)에서 `bg-mova-surface`,
  `text-mova-accent-bright`, `hover:bg-mova-surface-2` 등이 의도한 `var(--mova-*)`
  참조로 정상 생성됨을 직접 확인
- `pnpm lint`는 이 저장소에 `eslint` 바이너리가 설치돼 있지 않아(사전 존재하는
  환경 문제, 이 작업과 무관 — clean tree에서도 동일하게 실패) 실행 불가 확인만
  했다. `node_modules` 재설치 후 별도로 돌려볼 것.
