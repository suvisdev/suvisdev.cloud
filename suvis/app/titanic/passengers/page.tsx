"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://127.0.0.1:8000"

type PassengerPage = {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  items: Array<{
    id: number
    passenger_id: string
    survived: string
    pclass: string
    name: string
    gender: string
    age: string
    fare: string
    embarked: string
  }>
}

export default function TitanicPassengersPage() {
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [data, setData] = useState<PassengerPage | null>(null)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      setError("")
      try {
        const res = await fetch(`${API_BASE}/api/titanic/walter/passengers?page=${page}`)
        const body = (await res.json()) as PassengerPage | { detail?: string }
        if (!res.ok) throw new Error((body as { detail?: string }).detail || "승객 목록 조회 실패")
        if (!cancelled) setData(body as PassengerPage)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "승객 목록 조회 실패")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [page])

  const pageInfo = useMemo(() => {
    if (!data) return "데이터 없음"
    return `${data.page} / ${data.total_pages || 1} 페이지 · 총 ${data.total_count}명`
  }, [data])

  const pageNumbers = useMemo(() => {
    const total = data?.total_pages || 0
    if (total <= 0) return []
    const groupStart = Math.floor((page - 1) / 10) * 10 + 1
    const groupEnd = Math.min(groupStart + 9, total)
    return Array.from({ length: groupEnd - groupStart + 1 }, (_, i) => groupStart + i)
  }, [data, page])

  const startIndex = data ? (data.page - 1) * data.page_size + 1 : 0
  const endIndex = data ? Math.min(data.page * data.page_size, data.total_count) : 0

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#f3f3f3] px-4 py-4 md:px-6 md:py-6 dark:bg-[#0d0f14]">
      <main className="mx-auto grid max-w-[1500px] gap-4 md:grid-cols-[220px_1fr]">
        <aside className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-wide text-neutral-500">수업명</p>
          <div className="mt-4 space-y-2">
            <Link
              href="/lesson"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              LESSON 홈
            </Link>
            <Link
              href="/titanic"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              타이타닉
            </Link>
            <Link
              href="/titanic/data-collection"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              1. 데이터 수집
            </Link>
            <Link
              href="/titanic/passengers"
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
            >
              2. 승객목록
            </Link>
            <Link
              href="/titanic/smith-captain"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              3. 스미스 선장과 대화
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">VISION</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/vision"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              이미지 업로드
            </Link>
            <Link
              href="/vision/object-detection"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              객체 탐지
            </Link>
          </div>
        </aside>

        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">LESSON</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            타이타닉 승객 목록
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            업로드된 타이타닉 승객 데이터를 페이지당 50명 단위로 조회합니다.
          </p>

          <article className="mt-6 rounded-2xl border border-neutral-200 bg-gradient-to-b from-white to-neutral-50 p-5 shadow-sm dark:border-[#252b3b] dark:from-[#161a24] dark:to-[#1a1f2d]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  승객 목록 (페이지당 50명)
                </h2>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">{pageInfo}</p>
              </div>
              <div className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-medium text-neutral-700 dark:border-[#252b3b] dark:bg-[#252b3b] dark:text-neutral-300">
                현재 범위: {startIndex > 0 ? `${startIndex}-${endIndex}` : "-"}
              </div>
            </div>
            {error ? (
              <p className="mt-3 text-sm text-rose-700 dark:text-rose-400">{error}</p>
            ) : null}
            {loading ? (
              <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">불러오는 중...</p>
            ) : null}

            <div className="mt-4 overflow-auto rounded-xl border border-neutral-200 bg-white shadow-sm dark:border-[#252b3b] dark:bg-[#161a24]">
              <table className="min-w-full text-left text-sm">
                <thead className="sticky top-0 bg-neutral-100/95 text-neutral-900 backdrop-blur dark:bg-[#252b3b]/95 dark:text-neutral-100">
                  <tr>
                    <th className="px-3 py-3 font-semibold">PID</th>
                    <th className="px-3 py-3 font-semibold">Name</th>
                    <th className="px-3 py-3 font-semibold">Sex</th>
                    <th className="px-3 py-3 font-semibold">Age</th>
                    <th className="px-3 py-3 font-semibold">Pclass</th>
                    <th className="px-3 py-3 font-semibold">Survived</th>
                    <th className="px-3 py-3 font-semibold">Fare</th>
                    <th className="px-3 py-3 font-semibold">Embarked</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.items || []).map((row) => (
                    <tr
                      key={row.id}
                      className="border-t border-neutral-100 text-neutral-900 odd:bg-white even:bg-neutral-50/60 hover:bg-blue-50/40 dark:border-[#252b3b] dark:text-neutral-200 dark:odd:bg-[#161a24] dark:even:bg-[#1a1f2d]/60 dark:hover:bg-blue-900/20"
                    >
                      <td className="px-3 py-2.5 tabular-nums">{row.passenger_id}</td>
                      <td className="max-w-[260px] truncate px-3 py-2.5 font-medium">{row.name}</td>
                      <td className="px-3 py-2.5 capitalize">{row.gender || "-"}</td>
                      <td className="px-3 py-2.5 tabular-nums">{row.age || "-"}</td>
                      <td className="px-3 py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            row.pclass === "1"
                              ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
                              : row.pclass === "2"
                                ? "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
                                : row.pclass === "3"
                                  ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                                  : "bg-neutral-100 text-neutral-700 dark:bg-[#252b3b] dark:text-neutral-300"
                          }`}
                        >
                          {row.pclass ? `Class ${row.pclass}` : "-"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            row.survived === "1"
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                              : row.survived === "0"
                                ? "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"
                                : "bg-neutral-100 text-neutral-700 dark:bg-[#252b3b] dark:text-neutral-300"
                          }`}
                        >
                          {row.survived === "1" ? "Yes" : row.survived === "0" ? "No" : "-"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 tabular-nums">{row.fare || "-"}</td>
                      <td className="px-3 py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            row.embarked === "C"
                              ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                              : row.embarked === "Q"
                                ? "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300"
                                : row.embarked === "S"
                                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                                  : "bg-neutral-100 text-neutral-700 dark:bg-[#252b3b] dark:text-neutral-300"
                          }`}
                        >
                          {row.embarked ? row.embarked.toUpperCase() : "-"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
              {pageNumbers.map((n) => (
                <button
                  key={n}
                  type="button"
                  className={`rounded-md border px-2.5 py-1.5 transition-colors ${
                    n === page
                      ? "border-neutral-900 bg-neutral-900 font-semibold text-white dark:border-indigo-500 dark:bg-indigo-600"
                      : "border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-100 dark:border-[#252b3b] dark:bg-[#252b3b] dark:text-neutral-300 dark:hover:bg-[#2d3447]"
                  }`}
                  onClick={() => setPage(n)}
                  disabled={loading}
                >
                  {n}
                </button>
              ))}
              <button
                type="button"
                className="ml-1 rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-neutral-700 transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:text-neutral-400 dark:border-[#252b3b] dark:bg-[#252b3b] dark:text-neutral-300 dark:hover:bg-[#2d3447]"
                onClick={() => setPage((p) => p + 1)}
                disabled={loading || (data ? page >= (data.total_pages || 1) : true)}
              >
                다음
              </button>
            </div>
          </article>
        </section>
      </main>
    </div>
  )
}
