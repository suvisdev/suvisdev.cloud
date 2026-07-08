import Link from "next/link"
import { AppMuseumCard } from "@/components/apps/app-museum-card"
import { APPS_CATALOG, TEAM_PROJECTS } from "@/lib/apps-catalog"

export default function AppsPage() {
  return (
    <div className="relative min-h-[calc(100vh-5.5rem)] bg-[#ebe8e3] px-4 pb-6 pt-0 md:px-6">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04] dark:opacity-[0.015]"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")` }}
        aria-hidden
      />
      <main className="mx-auto flex min-h-[calc(100vh-5.5rem-1.5rem)] max-w-[1400px] flex-col py-8 md:py-12">
        <header className="mb-10 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <Link
              href="/"
              className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900"
            >
              ← 홈
            </Link>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-neutral-900 md:text-3xl">
              Suvisdev
            </h1>
            <p className="mt-1 text-sm font-medium tracking-[0.25em] text-neutral-500 uppercase">
              Online Apps
            </p>
          </div>
          <p className="max-w-md text-pretty break-keep text-sm leading-relaxed text-neutral-600 sm:max-w-lg">
            영화 추천부터 실험 기능까지, Suvisdev 앱을 한곳에서{" "}
            <span className="whitespace-nowrap">만나보세요.</span>
          </p>
        </header>

        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:gap-3">
          {APPS_CATALOG.map((app) => (
            <AppMuseumCard key={app.id} app={app} />
          ))}
        </div>

        <section className="mt-14">
          <div className="mb-6">
            <h2 className="text-xl font-bold tracking-tight text-neutral-900 md:text-2xl">
              Team Seuk
            </h2>
            <p className="mt-1 text-sm font-medium tracking-[0.25em] text-neutral-500 uppercase">
              Team Projects
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:gap-3">
            {TEAM_PROJECTS.map((app) => (
              <AppMuseumCard key={app.id} app={app} />
            ))}
          </div>
        </section>

        <footer className="mt-auto pt-10 text-center text-xs tracking-wide text-neutral-500">
          © {new Date().getFullYear()} Suvisdev. All rights reserved.
        </footer>
      </main>
    </div>
  )
}
