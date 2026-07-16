"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"

const tabs = [
  { href: "/admin/harvester/crawler", label: "크롤러" },
  { href: "/admin/harvester/scraper", label: "스크래퍼" },
]

export default function HarvesterLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <h1 className="text-2xl font-bold text-slate-800">수집기</h1>
      <p className="mt-1 text-sm text-slate-500">
        사이트를 고르고 자연어로 뭘 모을지 말하면, AI가 키워드·개수로 해석해서 실행합니다.
      </p>
      <nav className="mt-4 flex gap-1 border-b border-slate-200">
        {tabs.map(({ href, label }) => {
          const isActive = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                isActive
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {label}
            </Link>
          )
        })}
      </nav>
      <div className="mt-6">{children}</div>
    </div>
  )
}
