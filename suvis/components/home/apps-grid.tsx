import { Film, Ship } from "lucide-react"
import Link from "next/link"

const APPS = [
  {
    href: "/mova",
    label: "Mova",
    description: "AI 영화 추천",
    icon: Film,
    iconClassName: "h-7 w-7 text-red-400/95 transition-colors group-hover:text-cyan-400",
    tileClassName:
      "border border-red-900/55 bg-gradient-to-br from-red-950/80 via-zinc-950 to-zinc-950 shadow-md shadow-red-950/30 group-hover:border-amber-400/40 group-hover:shadow-amber-900/15",
    labelClassName: "text-red-200/60 group-hover:text-red-100/90",
  },
  {
    href: "/titanic",
    label: "Titanic",
    description: "승객 데이터 분석",
    icon: Ship,
    iconClassName: "h-7 w-7 text-sky-700 transition-colors group-hover:text-sky-900",
    tileClassName:
      "border border-sky-200 bg-gradient-to-br from-sky-50 to-white shadow-sm group-hover:border-sky-300",
    labelClassName: "text-sky-800/80 group-hover:text-sky-950",
  },
] as const

export function AppsGrid() {
  return (
    <div className="flex flex-wrap gap-8 sm:gap-10">
      {APPS.map((app) => {
        const Icon = app.icon
        return (
          <Link
            key={app.href}
            href={app.href}
            className="group flex w-28 flex-col items-center gap-2 sm:w-32"
          >
            <div
              className={`flex h-16 w-16 items-center justify-center rounded-2xl transition-all duration-200 group-hover:scale-105 sm:h-[4.25rem] sm:w-[4.25rem] ${app.tileClassName}`}
            >
              <Icon className={app.iconClassName} strokeWidth={1.75} aria-hidden />
            </div>
            <span
              className={`text-center text-sm font-semibold tracking-wide transition-colors ${app.labelClassName}`}
            >
              {app.label}
            </span>
            <span className="text-center text-xs text-neutral-500">{app.description}</span>
          </Link>
        )
      })}
    </div>
  )
}
