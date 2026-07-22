"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ChevronRight, Loader2 } from "lucide-react"
import { AdminMenuButton } from "../_components/admin-menu-button"
import { listApps, type AppHealth, type AppInfo } from "@/lib/admin-apps-api"

const healthBadge: Record<AppHealth, string> = {
  정상: "bg-emerald-100 text-emerald-700",
  점검: "bg-amber-100 text-amber-700",
  오류: "bg-red-100 text-red-700",
}

export default function AdminAppsPage() {
  const [apps, setApps] = useState<AppInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listApps()
      .then(setApps)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">앱 관리</h1>
            <p className="text-xs text-slate-400">SUVIS 서비스 앱 상태</p>
          </div>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {!apps ? (
          <div className="flex items-center justify-center py-20 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {apps.map((app) => (
              <div
                key={app.id}
                className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">{app.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${healthBadge[app.health]}`}>
                    {app.health}
                  </span>
                </div>
                <p className="line-clamp-2 text-sm text-slate-500">{app.description}</p>
                <div className="mt-1 flex items-center justify-end">
                  {app.href ? (
                    <Link
                      href={app.href}
                      target="_blank"
                      className="flex items-center gap-0.5 text-xs text-slate-400 transition-colors hover:text-emerald-600"
                    >
                      상세 보기 <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  ) : (
                    <span className="text-xs text-slate-300">상세 보기 불가</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
