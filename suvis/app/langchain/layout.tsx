import type { ReactNode } from "react"
import { AdminAuthGate } from "@/components/auth/admin-auth-gate"

export default function LangchainLayout({ children }: { children: ReactNode }) {
  return <AdminAuthGate>{children}</AdminAuthGate>
}
