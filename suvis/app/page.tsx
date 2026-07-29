import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { HeritadeHeadline } from "@/components/home/heritade-headline"
import { HeroImagePanel } from "@/components/home/hero-image-panel"

export default function Home() {
  return (
    <div className="min-h-[calc(100vh-4rem-1rem)] bg-[#e8e8e8] px-4 pt-3 pb-4 dark:bg-[#0d0f14] md:px-6 md:pt-4 md:pb-6">
      <main className="grid min-h-[calc(100vh-4rem-2.5rem)] gap-6 lg:grid-cols-2 lg:gap-8">
        <section className="flex flex-col justify-between gap-12 rounded-3xl bg-white px-6 py-8 dark:bg-[#161a24] sm:px-10 sm:py-10 lg:px-12 lg:py-14">
          <div className="space-y-10 md:space-y-12">
            <div className="flex items-start gap-6">
              <p className="flex-1 text-sm leading-[1.65] tracking-[-0.01em] text-neutral-700 dark:text-neutral-300 sm:text-[0.9375rem] sm:leading-[1.7]">
                웹·백엔드·AI를 아우르며, 확장 가능한 설계와 단순한 구현 사이의 균형을 맞춥니다.
                도메인별 AI 앱을 만들고, 지속 가능한 시스템을 구축합니다.
              </p>
              <ArrowUpRight
                className="mt-1 h-6 w-6 shrink-0 text-neutral-900 dark:text-neutral-100"
                strokeWidth={2}
                aria-hidden
              />
            </div>

            <hr className="border-neutral-300 dark:border-neutral-700" />

            <div className="overflow-hidden rounded-2xl border border-neutral-300 shadow-sm dark:border-neutral-700 lg:hidden">
              <HeroImagePanel compact />
            </div>

            <HeritadeHeadline />
          </div>

          <Link
            href="/contact"
            className="inline-flex w-full items-center justify-center rounded-2xl bg-[#f0dc3a] px-8 py-4 text-base font-bold text-neutral-900 shadow-sm transition-colors hover:bg-[#e8d020] sm:w-fit"
          >
            Suvisdev 알아보기
          </Link>
        </section>

        <section className="hidden min-h-[400px] overflow-hidden rounded-3xl border border-neutral-400/40 shadow-md dark:border-neutral-700/40 lg:block">
          <HeroImagePanel />
        </section>
      </main>
    </div>
  )
}
