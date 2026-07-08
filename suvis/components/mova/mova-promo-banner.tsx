import { Sparkles } from "lucide-react"
import Link from "next/link"

export function MovaPromoBanner() {
  return (
    <div className="relative overflow-hidden rounded-lg border border-[var(--mova-border)] bg-[var(--mova-surface)] px-4 py-3 md:px-6 md:py-3.5">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-[var(--mova-accent)] to-[var(--mova-ai)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_right,rgba(139,127,212,0.12),transparent_60%)]"
      />
      <div className="relative flex min-w-0 items-center justify-between gap-2 pl-2 sm:gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Sparkles className="h-4 w-4 shrink-0 text-[var(--mova-accent-bright)]" />
          <p className="min-w-0 text-xs font-medium leading-snug text-[var(--mova-text)] sm:text-sm md:text-base">
            Mova AI가 취향을 분석해 오늘의 추천을 준비했어요
          </p>
        </div>
        <Link
          href="/mova/main"
          className="hidden shrink-0 rounded-md border border-[var(--mova-border)] bg-[var(--mova-surface-2)] px-3 py-1 text-xs font-medium text-[var(--mova-text)] transition hover:bg-[var(--mova-surface)] sm:inline"
        >
          대화 시작
        </Link>
      </div>
    </div>
  )
}
