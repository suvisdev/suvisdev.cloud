"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"
import { AdminMenuButton } from "../_components/admin-menu-button"

const tabs = [
  { href: "/admin/stats/overview", label: "개요" },
  { href: "/admin/stats/visitors", label: "방문자" },
  { href: "/admin/stats/crawling", label: "크롤링" },
]

export default function StatsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex h-16 items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">통계</h1>
            <p className="text-xs text-slate-400">방문자·에이전트·크롤링 현황</p>
          </div>
        </div>
        <nav className="flex gap-1">
          {tabs.map(({ href, label }) => {
            const isActive = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                {label}
              </Link>
            )
          })}
        </nav>
      </header>

      <div className="p-4 md:p-6 lg:p-8">{children}</div>
    </div>
  )
}
