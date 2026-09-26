import Image from "next/image"
import { AppLauncher } from "@/components/home/app-launcher"
import { APPS_CATALOG, TEAM_PROJECTS } from "@/lib/apps-catalog"

const HOME_APPS = [...APPS_CATALOG, ...TEAM_PROJECTS]

export default function Home() {
  return (
    <div className="min-h-[calc(100vh-4rem-1rem)] bg-[#e8e8e8] px-4 dark:bg-[#0d0f14] md:px-6">
      <main className="mx-auto flex min-h-[calc(100vh-4rem-1rem)] w-full max-w-4xl flex-col items-center justify-center gap-10 py-16">
        <div className="flex items-center gap-3">
          <Image src="/suvis-logo.png" alt="" width={48} height={48} priority />
          <h1 className="text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-5xl">
            Suvisdev
          </h1>
        </div>
        <AppLauncher apps={HOME_APPS} />
      </main>
    </div>
  )
}
