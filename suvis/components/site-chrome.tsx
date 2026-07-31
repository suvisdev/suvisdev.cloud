"use client"

import { useEffect } from "react"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"
import { Header } from "@/components/header"
import { SuvisChatPanel } from "@/components/gemini-chat-panel"
import { VisitorTracker } from "@/components/visitor-tracker"

export function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { setTheme } = useTheme()
  const isAdminPath = pathname?.startsWith("/admin")
  const hideDefaultLayout = pathname?.startsWith("/mova") || isAdminPath

  // 다크 모드는 mova 전용이다. mova 밖(메인 사이트 전체, admin 포함)에서는
  // 토글 UI 자체가 없지만, mova에 들렀다 나온 세션이나 예전에 저장된
  // theme=dark가 next-themes localStorage에 남아 있으면 새로 진입할 때도
  // 그 값이 그대로 적용돼 버린다 — 그걸 여기서 매번 라이트로 되돌린다.
  useEffect(() => {
    if (!pathname?.startsWith("/mova")) {
      setTheme("light")
    }
  }, [pathname, setTheme])

  return (
    <>
      {/* 어드민 본인 트래픽은 방문자 집계에서 제외 */}
      {!isAdminPath && <VisitorTracker />}
      {!hideDefaultLayout && <Header />}
      {children}
      {!hideDefaultLayout && <SuvisChatPanel />}
    </>
  )
}
