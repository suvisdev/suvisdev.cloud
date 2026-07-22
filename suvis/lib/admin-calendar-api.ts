export type CalendarEventKind = "crawl" | "agent"

export type CalendarEvent = {
  id: string
  date: string // YYYY-MM-DD
  title: string
  kind: CalendarEventKind
}

function toDateKey(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function offsetDay(base: Date, days: number): Date {
  const d = new Date(base)
  d.setDate(d.getDate() + days)
  return d
}

/** TODO: harvester 스케줄 + 에이전트 invoke 예약 API 연동 전까지 mock. */
export async function listEvents(): Promise<CalendarEvent[]> {
  const today = new Date()
  return [
    { id: "1", date: toDateKey(offsetDay(today, -2)), title: "KOBIS 일간 박스오피스 수집", kind: "crawl" },
    { id: "2", date: toDateKey(today), title: "TMDB top_rated 수집", kind: "crawl" },
    { id: "3", date: toDateKey(today), title: "포스터 장르 분류기 정기 점검", kind: "agent" },
    { id: "4", date: toDateKey(offsetDay(today, 1)), title: "Echo 감성 분석 QLoRA 재학습", kind: "agent" },
    { id: "5", date: toDateKey(offsetDay(today, 3)), title: "chat_trend 랭킹 갱신", kind: "agent" },
    { id: "6", date: toDateKey(offsetDay(today, 5)), title: "KOFIC 주간 박스오피스 수집", kind: "crawl" },
    { id: "7", date: toDateKey(offsetDay(today, -6)), title: "네이버 영화 리뷰 크롤링", kind: "crawl" },
  ]
}
