import Image from "next/image"
import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { AppLauncher } from "@/components/home/app-launcher"
import { HeritadeHeadline } from "@/components/home/heritade-headline"
import { HeroImagePanel } from "@/components/home/hero-image-panel"
import { APPS_CATALOG, TEAM_PROJECTS } from "@/lib/apps-catalog"

const HOME_APPS = [...APPS_CATALOG, ...TEAM_PROJECTS]

/**
 * 홈 — 09-27 검색창·앱 타일 구조에 07월 컨셉(대형 콘덴스드 헤드라인 · 홀로그램 영상 패널 ·
 * 노란 CTA)을 다시 섞은 2열 레이아웃. 기능(AI 채팅·앱 진입)은 왼쪽 카드에 그대로 둔다.
 */
export default function Home() {
  return (
    <div className="min-h-[calc(100vh-4rem-1rem)] bg-[#e8e8e8] px-4 pt-3 pb-4 md:px-6 md:pt-4 md:pb-6 dark:bg-[#0d0f14]">
      <main className="grid min-h-[calc(100vh-4rem-2.5rem)] gap-6 lg:grid-cols-[1.15fr_1fr] lg:gap-8">
        <section className="flex flex-col gap-10 rounded-3xl bg-white px-6 py-8 sm:px-10 sm:py-10 lg:px-12 lg:py-12 dark:bg-[#161a24]">
          <div className="space-y-6">
            <div className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-2.5">
                <Image src="/suvis-logo.png" alt="" width={32} height={32} priority />
                <span className="text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
                  Suvisdev
                </span>
              </div>
              <ArrowUpRight
                className="h-6 w-6 shrink-0 text-neutral-900 dark:text-neutral-100"
                strokeWidth={2}
                aria-hidden
              />
            </div>
            <p className="max-w-xl text-sm leading-[1.65] tracking-[-0.01em] text-neutral-700 sm:text-[0.9375rem] sm:leading-[1.7] dark:text-neutral-300">
              웹·백엔드·AI를 아우르며, 확장 가능한 설계와 단순한 구현 사이의 균형을 맞춥니다.
              도메인별 AI 앱을 만들고, 지속 가능한 시스템을 구축합니다.
            </p>
          </div>

          <hr className="border-neutral-300 dark:border-neutral-700" />

          <div className="overflow-hidden rounded-2xl border border-neutral-300 shadow-sm lg:hidden dark:border-neutral-700">
            <HeroImagePanel compact />
          </div>

          <HeritadeHeadline />

          <AppLauncher apps={HOME_APPS} />

          <Link
            href="/contact"
            className="inline-flex w-full items-center justify-center rounded-2xl bg-[#f0dc3a] px-8 py-4 text-base font-bold text-neutral-900 shadow-sm transition-colors hover:bg-[#e8d020] sm:w-fit"
          >
            Suvisdev 알아보기
          </Link>
        </section>

        <section className="hidden min-h-[400px] overflow-hidden rounded-3xl border border-neutral-400/40 shadow-md lg:block dark:border-neutral-700/40">
          <HeroImagePanel />
        </section>
      </main>
    </div>
  )
}
