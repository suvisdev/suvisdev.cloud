"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2, Search, ShieldCheck, User } from "lucide-react"
import { AdminMenuButton } from "../_components/admin-menu-button"
import { listAdminUsers, type AdminUser } from "@/lib/admin-users-api"

type RoleFilter = "all" | "admin" | "user"

const PROVIDER_LABEL: Record<string, string> = {
  google: "Google",
  kakao: "Kakao",
  naver: "Naver",
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all")

  useEffect(() => {
    listAdminUsers()
      .then(setUsers)
      .catch((e: Error) => setError(e.message))
  }, [])

  const filtered = useMemo(() => {
    if (!users) return []
    return users.filter((u) => {
      const matchRole = roleFilter === "all" || u.role === roleFilter
      const q = search.toLowerCase()
      const matchSearch = !q || u.email.toLowerCase().includes(q) || u.nickname.toLowerCase().includes(q)
      return matchRole && matchSearch
    })
  }, [users, search, roleFilter])

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">사용자</h1>
            <p className="text-xs text-slate-400">로그인 사용자 관리</p>
          </div>
        </div>
        {users && (
          <span className="text-xs text-slate-400">
            전체 {users.length}명
          </span>
        )}
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {/* 필터 바 */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="이메일 또는 닉네임 검색"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            />
          </div>
          <div className="flex gap-1">
            {(["all", "admin", "user"] as RoleFilter[]).map((r) => (
              <button
                key={r}
                onClick={() => setRoleFilter(r)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  roleFilter === r
                    ? "bg-emerald-500 text-white"
                    : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {r === "all" ? "전체" : r === "admin" ? "관리자" : "사용자"}
              </button>
            ))}
          </div>
        </div>

        {!users ? (
          <div className="flex items-center justify-center py-20 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
            {filtered.length === 0 ? (
              <p className="px-5 py-10 text-center text-sm text-slate-400">
                {search || roleFilter !== "all" ? "검색 결과가 없습니다." : "사용자가 없습니다."}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs font-semibold text-slate-500">
                      <th className="px-5 py-3">이메일</th>
                      <th className="px-5 py-3">닉네임</th>
                      <th className="px-5 py-3">역할</th>
                      <th className="px-5 py-3">OAuth</th>
                      <th className="px-5 py-3">가입일</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((user) => (
                      <tr
                        key={user.id}
                        className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors"
                      >
                        <td className="px-5 py-3 text-slate-800">{user.email}</td>
                        <td className="px-5 py-3 text-slate-600">{user.nickname}</td>
                        <td className="px-5 py-3">
                          <RoleBadge role={user.role} />
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex gap-1 flex-wrap">
                            {user.providers.length === 0 ? (
                              <span className="text-xs text-slate-400">—</span>
                            ) : (
                              user.providers.map((p) => (
                                <span
                                  key={p}
                                  className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600"
                                >
                                  {PROVIDER_LABEL[p] ?? p}
                                </span>
                              ))
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-slate-400 text-xs whitespace-nowrap">
                          {new Date(user.created_at).toLocaleDateString("ko-KR")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function RoleBadge({ role }: { role: string }) {
  if (role === "admin") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
        <ShieldCheck className="h-3 w-3" />
        관리자
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
      <User className="h-3 w-3" />
      사용자
    </span>
  )
}
