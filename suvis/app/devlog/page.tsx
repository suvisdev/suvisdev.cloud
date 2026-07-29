import type { Metadata } from "next"
import { DEV_LOG } from "@/lib/devlog"

export const metadata: Metadata = {
  title: "DEVLOG | Suvisdev",
  description: "무엇을 만들었고 왜 그렇게 설계했는지에 대한 기록.",
}

const highlighted = DEV_LOG.filter((entry) => entry.highlighted)
const rest = DEV_LOG.filter((entry) => !entry.highlighted)

export default function DevLogPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#e8e8e8] px-4 pb-4 pt-0 dark:bg-[#0d0f14] md:px-6 md:pb-6">
      <main className="mx-auto max-w-[1100px] space-y-6">
        <section className="rounded-3xl bg-white px-6 py-10 dark:bg-[#161a24] sm:px-10 sm:py-12 lg:px-14">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500 dark:text-neutral-400">
            Devlog
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-4xl">
            무엇을 만들었고, 왜 그렇게 설계했나
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-[1.75] text-neutral-700 dark:text-neutral-300 sm:text-[0.9375rem]">
            기능을 나열하기보다, 각 작업에서 어떤 선택을 했고 무엇을 포기했는지를
            남깁니다. 결정의 근거가 결과보다 오래 남는다고 보기 때문입니다.
          </p>
        </section>

        <section className="rounded-3xl bg-white px-6 py-8 dark:bg-[#161a24] sm:px-10 sm:py-10 lg:px-14">
          <h2 className="text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            핵심 설계 판단
          </h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {highlighted.map((entry) => (
              <article
                key={entry.id}
                className="rounded-2xl border border-neutral-300 bg-[#fafafa] px-5 py-6 dark:border-neutral-700 dark:bg-[#1b2030]"
              >
                <h3 className="text-base font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
                  {entry.title}
                </h3>
                <p className="mt-3 text-sm leading-[1.7] text-neutral-700 dark:text-neutral-300">
                  {entry.intent}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-3xl bg-white px-6 py-8 dark:bg-[#161a24] sm:px-10 sm:py-10 lg:px-14">
          <h2 className="text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            만든 것들
          </h2>
          <ul className="mt-6 divide-y divide-neutral-200 dark:divide-neutral-700">
            {rest.map((entry) => (
              <li key={entry.id} className="py-5 first:pt-0 last:pb-0">
                <h3 className="text-sm font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-[0.9375rem]">
                  {entry.title}
                </h3>
                <p className="mt-2 text-sm leading-[1.7] text-neutral-600 dark:text-neutral-400">
                  {entry.intent}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  )
}
