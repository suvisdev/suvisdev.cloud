"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import type { ReactNode } from "react"
import { getSuvisSession, SUVIS_SESSION_CHANGED_EVENT } from "@/lib/suvis-session"

/** /admin 전체를 감싸는 프론트 UX 가드 — role!=admin이면 렌더 없이 홈으로 보낸다.
 * 실제 인가 최종 판정은 각 백엔드 API의 require_admin이 한다(여기는 UX 전용). */
export function AdminAuthGate({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [status, setStatus] = useState<"checking" | "allowed" | "denied">("checking")

  useEffect(() => {
    const check = () => {
      const session = getSuvisSession()
      if (session?.role === "admin") {
        setStatus("allowed")
      } else {
        setStatus("denied")
        router.replace("/")
      }
    }
    check()
    window.addEventListener(SUVIS_SESSION_CHANGED_EVENT, check)
    window.addEventListener("storage", check)
    return () => {
      window.removeEventListener(SUVIS_SESSION_CHANGED_EVENT, check)
      window.removeEventListener("storage", check)
    }
  }, [router])

  if (status !== "allowed") return null
  return <>{children}</>
}
