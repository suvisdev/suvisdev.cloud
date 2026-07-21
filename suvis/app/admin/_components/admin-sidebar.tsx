"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  Bot,
  CalendarDays,
  Home,
  Layers,
  Radar,
  Send,
  Settings,
  Users,
  X,
} from "lucide-react"
import { useAdminSidebar } from "./admin-sidebar-context"

const navItems = [
  { href: "/admin", label: "홈", icon: Home },
  { href: "/admin/apps", label: "앱 관리", icon: Layers },
  { href: "/admin/agents", label: "에이전트", icon: Bot },
  { href: "/admin/users", label: "사용자", icon: Users },
  { href: "/admin/calendar", label: "캘린더", icon: CalendarDays },
  { href: "/admin/stats", label: "통계", icon: BarChart3 },
  { href: "/admin/dispatch", label: "Dispatch", icon: Send },
  { href: "/admin/harvester", label: "수집기", icon: Radar },
  { href: "/admin/settings", label: "설정", icon: Settings },
]

export function AdminSidebar() {
  const pathname = usePathname()
  const { open, setOpen } = useAdminSidebar()

  return (
    <>
      {/* 데스크탑: 고정 왼쪽 사이드바 */}
      <aside className="fixed left-0 top-0 z-40 h-full w-16 flex-col border-r border-white/10 bg-[#1a1f2e] max-md:!hidden md:flex lg:w-60">
        <Link href="/" className="flex h-16 shrink-0 items-center border-b border-white/10 px-4 lg:px-6 hover:opacity-80 transition-opacity">
          <span className="text-base font-bold text-white lg:text-lg">
            <span className="hidden lg:inline">
              Suvis<span className="font-extrabold">dev</span>
            </span>
            <span className="text-xl font-extrabold text-emerald-400 lg:hidden">S</span>
          </span>
          <span className="ml-2 hidden rounded-md bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 lg:inline">
            Admin
          </span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto py-4 px-2">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span className="hidden lg:inline">{label}</span>
              </Link>
            )
          })}
        </nav>

        <div className="shrink-0 border-t border-white/10 p-3 lg:p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-sm font-bold text-white">
              A
            </div>
            <div className="hidden min-w-0 lg:block">
              <p className="truncate text-xs font-semibold text-white">Admin</p>
              <p className="truncate text-[10px] text-slate-400">ssuvisdev@gmail.com</p>
            </div>
          </div>
        </div>
      </aside>

      {/* 모바일: 드로어 오버레이 */}
      {open && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          onClick={() => setOpen(false)}
        >
          <div className="absolute inset-0 bg-black/50" />

          <aside
            className="absolute left-0 top-0 h-full w-64 flex-col bg-[#1a1f2e] flex"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex h-16 items-center justify-between border-b border-white/10 px-5">
              <Link href="/" onClick={() => setOpen(false)} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                <span className="text-lg font-bold text-white">
                  Suvis<span className="font-extrabold">dev</span>
                </span>
                <span className="rounded-md bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400">
                  Admin
                </span>
              </Link>
              <button
                onClick={() => setOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5 hover:text-white"
                aria-label="메뉴 닫기"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <nav className="flex flex-1 flex-col gap-1 overflow-y-auto py-4 px-3">
              {navItems.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "text-slate-400 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    {label}
                  </Link>
                )
              })}
            </nav>

            <div className="shrink-0 border-t border-white/10 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-sm font-bold text-white">
                  A
                </div>
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-white">Admin</p>
                  <p className="truncate text-[10px] text-slate-400">ssuvisdev@gmail.com</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* 모바일: 하단 탭바 */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-white/10 bg-[#1a1f2e] md:hidden">
        {navItems.slice(0, 5).map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors ${
                isActive ? "text-emerald-400" : "text-slate-400"
              }`}
            >
              <Icon className="h-5 w-5" />
              {label}
            </Link>
          )
        })}
      </nav>
    </>
  )
}
