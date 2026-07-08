"use client"

import { usePathname } from "next/navigation"
import { Header } from "@/components/header"
import { SuvisChatPanel } from "@/components/gemini-chat-panel"

export function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const hideDefaultLayout =
    pathname?.startsWith("/mova") || pathname?.startsWith("/admin")

  return (
    <>
      {!hideDefaultLayout && <Header />}
      {children}
      {!hideDefaultLayout && <SuvisChatPanel />}
    </>
  )
}
