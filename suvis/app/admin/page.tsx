import {
  AlertCircle,
  ArrowUpRight,
  Bell,
  ChevronRight,
  Clock,
  Database,
  FileText,
  Plus,
  Send,
  Zap,
} from "lucide-react"
import { AdminMenuButton } from "./_components/admin-menu-button"

/* ─────────────────────────── 정적 데이터 ─────────────────────────── */

const apps = [
  {
    name: "Titanic",
    desc: "타이타닉 ML 대시보드",
    status: "운영중" as const,
    updated: "2025.06.15",
    color: "blue",
    route: "/titanic",
    endpoints: 8,
  },
  {
    name: "Mova",
    desc: "영화 AI 플랫폼",
    status: "운영중" as const,
    updated: "2025.06.10",
    color: "violet",
    route: "/mova",
    endpoints: 12,
  },
  {
    name: "Silicon Valley",
    desc: "API 스켈레톤 구축 중",
    status: "개발중" as const,
    updated: "2025.06.19",
    color: "emerald",
    route: "#",
    endpoints: 5,
  },
  {
    name: "Friday 13th",
    desc: "개발 예정",
    status: "예정" as const,
    updated: "-",
    color: "orange",
    route: "#",
    endpoints: 0,
  },
  {
    name: "Imitation Game",
    desc: "개발 예정",
    status: "예정" as const,
    updated: "-",
    color: "rose",
    route: "#",
    endpoints: 0,
  },
]

const schedule = [
  { time: "10:00", label: "Silicon Valley 스켈레톤 완성", dot: "bg-emerald-500" },
  { time: "14:00", label: "DB 마이그레이션 검토", dot: "bg-blue-500" },
  { time: "16:00", label: "Mova API 서버 점검", dot: "bg-violet-500" },
  { time: "19:00", label: "코드 리뷰", dot: "bg-slate-400" },
]

const announcements = [
  { text: "Silicon Valley 스켈레톤 구조 완성", date: "2025.06.19", hot: true },
  { text: "Mova AI 채팅 기능 업데이트", date: "2025.06.10", hot: false },
  { text: "DB 스키마 최적화 완료", date: "2025.06.05", hot: false },
  { text: "titanic 선장 채팅 페이지 리디자인", date: "2025.05.28", hot: false },
]

const apiStats = [
  { label: "Titanic", calls: 120, max: 200, color: "bg-blue-500" },
  { label: "Mova", calls: 200, max: 200, color: "bg-violet-500" },
  { label: "Silicon Valley", calls: 40, max: 200, color: "bg-emerald-500" },
]

const weekDays = ["일", "월", "화", "수", "목", "금", "토"]
const calendarWeek = [15, 16, 17, 18, 19, 20, 21]
const today = 19

const statusColor: Record<string, string> = {
  운영중: "bg-emerald-100 text-emerald-700",
  개발중: "bg-amber-100 text-amber-700",
  예정: "bg-slate-100 text-slate-500",
}

const cardAccent: Record<string, string> = {
  blue: "border-t-blue-500",
  violet: "border-t-violet-500",
  emerald: "border-t-emerald-500",
  orange: "border-t-orange-400",
  rose: "border-t-rose-400",
}

const cardBg: Record<string, string> = {
  blue: "bg-blue-50",
  violet: "bg-violet-50",
  emerald: "bg-emerald-50",
  orange: "bg-orange-50",
  rose: "bg-rose-50",
}

/* ─────────────────────────────── 페이지 ─────────────────────────── */

export default function AdminPage() {
  return (
    <div className="min-h-screen">
      {/* ── 상단 헤더 바 ── */}
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">대시보드</h1>
            <p className="text-xs text-slate-400">오늘, 목요일 · 2025년 6월 19일</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="relative rounded-full p-2 text-slate-500 hover:bg-slate-100"
            aria-label="알림"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-emerald-500" />
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-sm font-bold text-white">
            A
          </div>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {/* ── 알림 배너 ── */}
        <div className="mb-6 flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            개발 중인 앱이 3개 있어요
          </div>
          <button type="button" className="flex items-center gap-1 text-xs font-semibold text-amber-600 hover:text-amber-800">
            더보기 <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* ── 앱 현황 + 캘린더 ── */}
        <div className="mb-6 grid gap-6 lg:grid-cols-[1fr_300px] xl:grid-cols-[1fr_320px]">
          {/* 앱 현황 */}
          <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800">앱 현황</h2>
              <div className="flex gap-1.5 text-xs">
                <span className="rounded-full bg-emerald-100 px-2.5 py-1 font-medium text-emerald-700">운영중 2</span>
                <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-700">개발중 3</span>
              </div>
            </div>

            {/* 가로 스크롤 카드 */}
            <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 snap-x snap-mandatory scroll-smooth">
              {apps.map((app) => (
                <div
                  key={app.name}
                  className={`min-w-[160px] flex-shrink-0 snap-start rounded-xl border border-t-4 bg-white shadow-sm ${cardAccent[app.color]}`}
                >
                  <div className={`rounded-t-lg px-3 pt-3 pb-2 ${cardBg[app.color]}`}>
                    <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusColor[app.status]}`}>
                      {app.status}
                    </span>
                    <p className="mt-1.5 text-sm font-bold text-slate-800">{app.name}</p>
                    <p className="text-[11px] text-slate-500">{app.desc}</p>
                  </div>
                  <div className="px-3 py-2">
                    <p className="text-[10px] text-slate-400">
                      엔드포인트 <span className="font-semibold text-slate-600">{app.endpoints}개</span>
                    </p>
                    <p className="mt-0.5 text-[10px] text-slate-400">{app.updated} 업데이트</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 캘린더 + 일정 */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400">오늘, 목요일</p>
                <p className="text-sm font-bold text-slate-800">2025년 6월</p>
              </div>
              <button type="button" className="text-xs font-medium text-emerald-600 hover:text-emerald-800">
                더보기
              </button>
            </div>

            {/* 주간 캘린더 */}
            <div className="mb-4 grid grid-cols-7 gap-1 text-center">
              {weekDays.map((d) => (
                <div key={d} className="text-[10px] font-medium text-slate-400">{d}</div>
              ))}
              {calendarWeek.map((day) => (
                <div
                  key={day}
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium mx-auto ${
                    day === today
                      ? "bg-emerald-500 text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {day}
                </div>
              ))}
            </div>

            {/* 오늘 일정 */}
            <div className="space-y-2.5">
              {schedule.map((item) => (
                <div key={item.time} className="flex items-start gap-2.5">
                  <div className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${item.dot}`} />
                  <div>
                    <p className="text-[11px] font-semibold text-slate-700">{item.label}</p>
                    <p className="text-[10px] text-slate-400 flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {item.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* ── 빠른 액션 ── */}
        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold text-slate-800">빠른 액션</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {[
              { label: "새 앱 등록", icon: Plus, color: "bg-emerald-50 text-emerald-600", href: "#" },
              { label: "API 엔드포인트 추가", icon: Zap, color: "bg-blue-50 text-blue-600", href: "#" },
              { label: "DB 마이그레이션", icon: Database, color: "bg-violet-50 text-violet-600", href: "#" },
              { label: "자주 묻는 질문 FAQ", icon: FileText, color: "bg-amber-50 text-amber-600", href: "#" },
              { label: "Dispatch", icon: Send, color: "bg-indigo-50 text-indigo-600", href: "/admin/dispatch" },
            ].map(({ label, icon: Icon, color, href }) => (
              <a
                key={label}
                href={href}
                className={`flex flex-col items-center gap-2 rounded-xl p-4 text-center transition-opacity hover:opacity-80 ${color}`}
              >
                <Icon className="h-6 w-6" />
                <span className="text-xs font-medium leading-tight">{label}</span>
              </a>
            ))}
          </div>
        </section>

        {/* ── 월간 보고서 통계 ── */}
        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-800">2025년 6월 보고서</h2>
            <button type="button" className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-700">
              더보기 <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "총 앱 수", value: "5개", badge: "↑ 1", badgeColor: "text-emerald-600 bg-emerald-50" },
              { label: "운영중 앱", value: "2개", badge: "안정", badgeColor: "text-emerald-600 bg-emerald-50" },
              { label: "개발중 앱", value: "3개", badge: "↓ 1", badgeColor: "text-amber-600 bg-amber-50" },
              { label: "이번 달 배포", value: "2건", badge: "↑ 1", badgeColor: "text-blue-600 bg-blue-50" },
            ].map(({ label, value, badge, badgeColor }) => (
              <div key={label} className="rounded-xl bg-slate-50 px-4 py-3">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-bold text-slate-800">{value}</p>
                <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${badgeColor}`}>
                  {badge}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ── API 호출 현황 + 공지사항 ── */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* API 호출 차트 */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800">API 호출 현황</h2>
              <span className="text-xs text-slate-400">이번 달 기준</span>
            </div>
            <div className="space-y-4">
              {apiStats.map(({ label, calls, max, color }) => (
                <div key={label}>
                  <div className="mb-1.5 flex justify-between text-xs">
                    <span className="font-medium text-slate-700">{label}</span>
                    <span className="font-semibold text-slate-800">{calls}건</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-2 rounded-full ${color}`}
                      style={{ width: `${(calls / max) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
              총 <span className="font-semibold text-slate-700">360건</span> 처리됨
            </div>
          </section>

          {/* 공지사항 */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800">최근 공지사항</h2>
              <button type="button" className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-700">
                더보기 <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </div>
            <ul className="space-y-3">
              {announcements.map(({ text, date, hot }) => (
                <li key={text} className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 min-w-0">
                    {hot && (
                      <span className="mt-0.5 shrink-0 rounded bg-rose-500 px-1 py-0.5 text-[9px] font-bold text-white">
                        NEW
                      </span>
                    )}
                    <p className="truncate text-xs text-slate-700">{text}</p>
                  </div>
                  <span className="shrink-0 text-[10px] text-slate-400">{date}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
