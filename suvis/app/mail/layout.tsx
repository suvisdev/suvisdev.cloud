import type { ReactNode } from "react"
import { AdminAuthGate } from "@/components/auth/admin-auth-gate"

// mail/contacts가 require_admin이 걸린 dispatch adress 백엔드를 호출하므로
// 페이지 진입 자체를 관리자 전용으로 잠근다(2026-08-27, PROGRESS 백로그 종결).
export default function MailLayout({ children }: { children: ReactNode }) {
  return <AdminAuthGate>{children}</AdminAuthGate>
}
