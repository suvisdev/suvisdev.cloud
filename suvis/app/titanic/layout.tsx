import type { ReactNode } from "react"
import { AdminAuthGate } from "@/components/auth/admin-auth-gate"

export default function TitanicLayout({ children }: { children: ReactNode }) {
  return <AdminAuthGate>{children}</AdminAuthGate>
}
