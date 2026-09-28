import Image from "next/image"
import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { AppLauncher } from "@/components/home/app-launcher"
import { APPS_CATALOG, TEAM_PROJECTS } from "@/lib/apps-catalog"

const HOME_APPS = [...APPS_CATALOG, ...TEAM_PROJECTS]

/**
 * 홈 — 09-27 심플 구조(로고 → AI 채팅 → 앱 타일)를 유지하고, 07월 컨셉에서 포인트만 가져온다:
 * 콘덴스드 디스플레이 헤드라인(회색/검정 교차)과 노란 악센트(#f0dc3a). 2열 카드·영상 패널은 쓰지 않는다
 * (2026-09-28 사용자: "심플하게 가는데 포인트만 컨셉 따와서").
 */
export default function Home() {
  return (
    <div className="min-h-[calc(100vh-4rem-1rem)] bg-[#e8e8e8] px-4 md:px-6 dark:bg-[#0d0f14]">
      <main className="mx-auto flex min-h-[calc(100vh-4rem-1rem)] w-full max-w-4xl flex-col items-center justify-center gap-10 py-16">
        <div className="flex flex-col items-center gap-5 text-center">
          <div className="flex items-center gap-3">
            <Image src="/suvis-logo.png" alt="" width={40} height={40} priority />
            <span className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
              Suvisdev
            </span>
          </div>
          <h1 className="font-display text-[clamp(2rem,5vw,3.5rem)] leading-[0.95] font-bold tracking-[-0.01em] uppercase">
            <span className="block">
              <span className="text-[#b3b3b3]">Simplify</span>{" "}
              <span className="text-neutral-900 dark:text-neutral-100">Complexity,</span>
            </span>
            <span className="block">
              <span className="text-[#b3b3b3]">Scale</span>{" "}
              <span className="text-neutral-900 dark:text-neutral-100">Without Limits.</span>
            </span>
          </h1>
        </div>

        <AppLauncher apps={HOME_APPS} />

        <Link
          href="/contact"
          className="group inline-flex items-center gap-2 text-sm font-semibold text-neutral-800 dark:text-neutral-200"
        >
          Suvisdev 알아보기
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-[#f0dc3a] text-neutral-900 transition-colors group-hover:bg-[#e8d020]">
            <ArrowUpRight className="h-4 w-4" strokeWidth={2} aria-hidden />
          </span>
        </Link>
      </main>
    </div>
  )
}
