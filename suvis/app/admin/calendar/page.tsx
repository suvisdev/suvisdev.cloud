"use client"

import { useEffect, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react"
import { AdminMenuButton } from "../_components/admin-menu-button"
import { listEvents, type CalendarEvent } from "@/lib/admin-calendar-api"

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"]

function dateKey(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`
}

function buildMonthGrid(year: number, month: number): (number | null)[] {
  const firstDow = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = Array(firstDow).fill(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

export default function AdminCalendarPage() {
  const now = new Date()
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const [selected, setSelected] = useState(dateKey(now.getFullYear(), now.getMonth(), now.getDate()))
  const [events, setEvents] = useState<CalendarEvent[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listEvents()
      .then(setEvents)
      .catch((e: Error) => setError(e.message))
  }, [])

  const grid = useMemo(() => buildMonthGrid(cursor.year, cursor.month), [cursor])
  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>()
    for (const ev of events ?? []) {
      const list = map.get(ev.date) ?? []
      list.push(ev)
      map.set(ev.date, list)
    }
    return map
  }, [events])

  const todayKey = dateKey(now.getFullYear(), now.getMonth(), now.getDate())
  const selectedEvents = eventsByDate.get(selected) ?? []

  const goMonth = (delta: number) => {
    setCursor((prev) => {
      const d = new Date(prev.year, prev.month + delta, 1)
      return { year: d.getFullYear(), month: d.getMonth() }
    })
  }

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">캘린더</h1>
            <p className="text-xs text-slate-400">크롤링 스케줄·에이전트 실행 예약</p>
          </div>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {!events ? (
          <div className="flex items-center justify-center py-20 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-800">
                  {cursor.year}년 {cursor.month + 1}월
                </h2>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => goMonth(-1)}
                    className="flex h-7 w-7 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    aria-label="이전 달"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setCursor({ year: now.getFullYear(), month: now.getMonth() })}
                    className="rounded-full border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                  >
                    오늘
                  </button>
                  <button
                    type="button"
                    onClick={() => goMonth(1)}
                    className="flex h-7 w-7 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    aria-label="다음 달"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-medium text-slate-400">
                {WEEKDAYS.map((w) => (
                  <div key={w} className="py-1.5">
                    {w}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-1">
                {grid.map((d, i) => {
                  if (d === null) return <div key={i} />
                  const key = dateKey(cursor.year, cursor.month, d)
                  const dayEvents = eventsByDate.get(key) ?? []
                  const isSelected = key === selected
                  const isToday = key === todayKey
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelected(key)}
                      className={`flex aspect-square flex-col items-center justify-start gap-1 rounded-xl px-1 py-1.5 text-xs transition-colors ${
                        isSelected ? "bg-emerald-100 text-emerald-700" : "text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <span
                        className={`flex h-5 w-5 items-center justify-center rounded-full ${
                          isToday && !isSelected ? "bg-slate-800 text-white" : ""
                        } ${isSelected ? "font-bold" : ""}`}
                      >
                        {d}
                      </span>
                      <span className="flex gap-0.5">
                        {dayEvents.slice(0, 3).map((ev) => (
                          <span
                            key={ev.id}
                            className={`h-1.5 w-1.5 rounded-full ${
                              ev.kind === "agent" ? "bg-violet-500" : "bg-blue-500"
                            }`}
                          />
                        ))}
                      </span>
                    </button>
                  )
                })}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-4 text-sm font-bold text-slate-800">{selected} 일정</h2>
              {selectedEvents.length === 0 ? (
                <p className="text-xs text-slate-400">해당 날짜에 등록된 일정이 없습니다.</p>
              ) : (
                <ul className="space-y-3">
                  {selectedEvents.map((ev) => (
                    <li key={ev.id} className="flex items-start gap-2.5">
                      <span
                        className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                          ev.kind === "agent" ? "bg-violet-500" : "bg-blue-500"
                        }`}
                      />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-slate-700">{ev.title}</p>
                        <p className="text-[10px] text-slate-400">{ev.kind === "agent" ? "에이전트" : "크롤링"}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
