import type { Metadata } from "next"
import Link from "next/link"
import "./gildle.css"

export const metadata: Metadata = {
  title: "Gildle — 반려견 산책 경로 추천",
  description: "나무 그늘, 위험구역 회피, 계절별 가중치 기반 반려견 친화 산책 경로 추천 앱",
}

export default function GildleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="gildle-app flex min-h-screen flex-col">
      {children}
      <footer className="mt-auto border-t border-gildle-border bg-gildle-surface/60">
        <div className="mx-auto flex max-w-[1400px] flex-col gap-1 px-4 py-3 md:px-6">
          <nav className="flex flex-col gap-0.5 text-[10px] text-gildle-muted md:flex-row md:flex-wrap md:items-center md:gap-x-2 md:gap-y-0.5">
            <Link href="/terms" className="hover:text-gildle-text">
              이용약관
            </Link>
            <span className="hidden text-neutral-600 md:inline" aria-hidden>
              ·
            </span>
            <Link href="/privacy" className="hover:text-gildle-text">
              개인정보 처리방침
            </Link>
            <span className="hidden text-neutral-600 md:inline" aria-hidden>
              ·
            </span>
            <a href="mailto:ssuvisdev@gmail.com" className="hover:text-gildle-text">
              문의
            </a>
          </nav>
          <p className="text-[10px] text-neutral-500">© 2026 SUVIS · gildle</p>
        </div>
      </footer>
    </div>
  )
}
