import type { ReactNode } from "react"
import { AdminAuthGate } from "@/components/auth/admin-auth-gate"

// 텔레그램 발송 데모가 require_admin이 걸린 dispatch telegram 백엔드를 호출하므로
// 페이지 진입 자체를 관리자 전용으로 잠근다(2026-08-27, /mail과 동일 정리).
export default function TelegramLayout({ children }: { children: ReactNode }) {
  return <AdminAuthGate>{children}</AdminAuthGate>
}
