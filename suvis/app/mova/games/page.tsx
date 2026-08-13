import Link from "next/link"
import { Brain, Layers } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"

export const metadata = { title: "미니게임 · Mova" }

const GAMES = [
  {
    href: "/mova/games/chosung",
    icon: Brain,
    title: "영화 초성 게임",
    desc: "초성을 보고 영화 제목을 맞혀요. 힌트는 최대 3개 · 1분 안에 몇 개 맞히나요?",
    accent: "from-fuchsia-500/25 to-indigo-500/10",
  },
  {
    href: "/mova/games/memory",
    icon: Layers,
    title: "카드 뒤집기",
    desc: "포스터와 제목 카드를 짝지어 뒤집어요. 1단계(4장) → 10단계(40장). 빠를수록 상위.",
    accent: "from-emerald-500/25 to-teal-500/10",
  },
] as const

export default function GamesHubPage() {
  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[900px] space-y-6 px-4 py-6 md:px-6 md:py-8">
        <header className="space-y-1">
          <h1 className="text-xl font-semibold text-mova-text md:text-2xl">미니게임</h1>
          <p className="text-sm text-mova-muted">
            로그인하면 리더보드에 기록이 남고 내 등수를 볼 수 있어요. 비로그인도 플레이는 가능해요.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          {GAMES.map(({ href, icon: Icon, title, desc, accent }) => (
            <Link
              key={href}
              href={href}
              className={`group relative overflow-hidden rounded-2xl border border-mova-border bg-gradient-to-br ${accent} p-6 transition hover:border-mova-accent/40`}
            >
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-mova-surface text-mova-accent-bright ring-1 ring-mova-border">
                <Icon className="h-5 w-5" />
              </div>
              <h2 className="text-lg font-semibold text-mova-text">{title}</h2>
              <p className="mt-1.5 text-sm text-mova-muted">{desc}</p>
              <p className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-mova-accent-bright">
                시작하기 →
              </p>
            </Link>
          ))}
        </div>
      </main>
    </>
  )
}
