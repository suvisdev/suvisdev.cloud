"use client"

import { usePathname } from "next/navigation"
import { Wrench } from "lucide-react"

// 점검 중에도 열어 두는 페이지 — 스토어 심사·법적 고지가 가리키는 주소라 막으면 안 된다.
const ALWAYS_OPEN = ["/privacy", "/terms", "/account-deletion"]

/** 점검 모드가 켜진 서비스면 본문 대신 안내를 띄운다(헤더·푸터는 레이아웃이 그대로 둔다). */
export function MaintenanceGate({
  on,
  name,
  children,
}: {
  on: boolean
  name: string
  children: React.ReactNode
}) {
  const pathname = usePathname() ?? ""
  if (!on || ALWAYS_OPEN.some((p) => pathname.endsWith(p))) return <>{children}</>
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-24">
      <div className="max-w-sm text-center">
        <Wrench className="mx-auto mb-4 h-8 w-8 opacity-60" />
        <h1 className="mb-2 text-lg font-bold">{name} 점검 중입니다</h1>
        <p className="text-sm opacity-70">
          더 나은 서비스를 위해 잠시 점검하고 있어요. 잠시 후 다시 이용해 주세요.
        </p>
      </div>
    </main>
  )
}
