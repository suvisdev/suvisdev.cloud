"use client"

import { usePathname } from "next/navigation"
import { Header } from "@/components/header"
import { VisitorTracker } from "@/components/visitor-tracker"

export function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAdminPath = pathname?.startsWith("/admin")
  const hideDefaultLayout = pathname?.startsWith("/mova") || isAdminPath

  return (
    <>
      {/* 어드민 본인 트래픽은 방문자 집계에서 제외 */}
      {!isAdminPath && <VisitorTracker />}
      {!hideDefaultLayout && <Header />}
      {children}
    </>
  )
}
