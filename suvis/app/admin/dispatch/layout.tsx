"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"

const tabs = [
  { href: "/admin/dispatch/mail", label: "메일 발송" },
  { href: "/admin/dispatch/telegram", label: "텔레그램" },
  { href: "/admin/dispatch/contacts", label: "주소록" },
  { href: "/admin/dispatch/receive", label: "수신함" },
]

export default function DispatchLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <h1 className="text-2xl font-bold text-slate-800">Dispatch</h1>
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
