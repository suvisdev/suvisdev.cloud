# Suvisdev — 테마(라이트/다크) 명세

> 2026-09-28 사용자 결정으로 **경로 고정 테마**가 됐다. 이전 판의 "사용자 토글·OS 설정 감지" 지시는
> 폐기됐다(2026-10-20 이 문서 갱신). 토글·테마 저장 기능을 다시 만들지 않는다.

## 기본 방침

| 경로 | 테마 |
|------|------|
| `/mova/**` | 다크 |
| 그 외 전부(메인·gildle·admin·lesson 등) | 라이트 |

- 사용자가 바꾸는 수단은 없다 — `ThemeToggle`·`useTheme().setTheme` 호출 코드는 저장소에서 삭제됐다.
- OS 다크모드 설정도 보지 않는다(`enableSystem={false}`).

## 구현 (현행 코드)

- `app/layout.tsx` — `<ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>`
- `components/theme-provider.tsx` — `usePathname()`으로 `forcedTheme`를 `/mova`로 시작하면 `"dark"`,
  아니면 `"light"`로 항상 넘긴다. `forcedTheme`는 localStorage를 읽지도 쓰지도 않아서, 예전 방식
  (진입 시 `setTheme`)에서 탭 간 storage 동기화로 mova 탭이 라이트로 뒤집히던 문제가 생기지 않는다.
- Tailwind v4 — `tailwind.config.js`는 없다. `app/globals.css`의
  `@custom-variant dark (&:is(.dark *));`와 `.dark { … }` 토큰 블록이 `dark:` 변형을 정의한다.

## 새 서브앱을 다크로 두어야 할 때

`components/theme-provider.tsx`의 경로 조건에 그 경로를 추가한다. 페이지 안에서 `setTheme`을 부르거나
`.dark` 클래스를 직접 붙이지 않는다.

## 색상

색상 토큰·`dark:` 사용 규칙은 `_docs/DESIGN.md`가 기준이다(shadcn 토큰, mova는 `bg-mova-*` 명명 유틸리티).
라이트 고정 경로의 기존 `dark:` 클래스는 지금은 적용되지 않지만, 지우는 정리는 별도 작업으로 한다.
