import { AppLauncher } from "@/components/home/app-launcher"
import { APPS_CATALOG, TEAM_PROJECTS } from "@/lib/apps-catalog"

const HOME_APPS = [...APPS_CATALOG, ...TEAM_PROJECTS]

/** 홈 — 제목 → AI 채팅 → 앱 타일. 로고 이미지·헤드라인·CTA는 뺐다(2026-09-28 사용자). */
export default function Home() {
  return (
    <div className="home-grid-bg min-h-[calc(100vh-4rem-1rem)] px-4 md:px-6 dark:bg-[#0d0f14]">
      <main className="mx-auto flex min-h-[calc(100vh-4rem-1rem)] w-full max-w-4xl flex-col items-center justify-center gap-10 py-16">
        <h1 className="text-4xl font-bold tracking-tight text-neutral-900 sm:text-5xl dark:text-neutral-100">
          Suvisdev
        </h1>
        <AppLauncher apps={HOME_APPS} />
      </main>
    </div>
  )
}
