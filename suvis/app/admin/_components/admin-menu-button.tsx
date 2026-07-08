"use client"

import { Menu } from "lucide-react"
import { useAdminSidebar } from "./admin-sidebar-context"

export function AdminMenuButton() {
  const { setOpen } = useAdminSidebar()
  return (
    <button
      onClick={() => setOpen(true)}
      className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 md:hidden"
      aria-label="메뉴 열기"
    >
      <Menu className="h-5 w-5" />
    </button>
  )
}
