"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes"

/**
 * 테마는 경로로만 정해진다 — mova(`/mova/**`)는 다크, 그 밖은 라이트(2026-09-28 사용자 결정).
 * 토글·`setTheme`로 바꾸는 코드는 없다. `forcedTheme`는 저장값(localStorage)을 읽지도 쓰지도
 * 않아 탭 간 storage 동기화로 뒤집히던 문제(09-28)도 생기지 않는다.
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  const pathname = usePathname()
  const forcedTheme = pathname?.startsWith("/mova") ? "dark" : "light"
  return (
    <NextThemesProvider {...props} forcedTheme={forcedTheme}>
      {children}
    </NextThemesProvider>
  )
}
