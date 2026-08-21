import Link from "next/link"
import { TreePine, ShieldCheck, Route, Dog, MapPin, Thermometer } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"

const FEATURES = [
  {
    icon: TreePine,
    title: "나무 그늘 우선 경로",
    description:
      "OSM 보행 그래프에서 tree_score가 높은 구간을 우선 연결합니다. 여름엔 그늘이 많은 길, 가을엔 단풍길을 자동으로 가중합니다.",
  },
  {
    icon: ShieldCheck,
    title: "위험구역 자동 회피",
    description:
      "도로교통공단 결빙 데이터와 hazard_score를 결합해 빙판·급경사·공사 구간을 우회합니다. 계절별 위험도가 실시간으로 반영됩니다.",
  },
  {
    icon: Dog,
    title: "반려견 친화 점수",
    description:
      "dog_friendly_score로 반려견 동반 가능 공원, 펫 프리 존, 넓은 보도를 우선 배정합니다. 소형견·대형견별 추천이 달라집니다.",
  },
] as const

const DATA_SOURCES = [
  { icon: MapPin, label: "OSM 보행 그래프" },
  { icon: Thermometer, label: "도로교통공단 결빙 데이터" },
  { icon: Route, label: "실시간 경로 가중치" },
] as const

export default function GildlePage() {
  return (
    <main className="gildle-nature-bg gildle-grain relative flex min-h-screen min-w-0 flex-col overflow-x-clip">
      <header className="relative z-20 flex h-11 shrink-0 items-center justify-between px-4 sm:h-12 sm:px-6">
        <Link
          href="/"
          className="text-xs text-gildle-muted transition-colors hover:text-gildle-text"
        >
          ← suvisdev.cloud
        </Link>
        <ThemeToggle />
      </header>

      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:py-16">
        <section className="w-full max-w-2xl text-center">
          <p className="mb-2 text-[10px] font-medium tracking-[0.18em] text-gildle-muted uppercase sm:mb-3 sm:text-xs sm:tracking-[0.2em]">
            반려견 산책 경로 추천
          </p>

          <h1 className="text-3xl font-bold leading-tight tracking-tight text-gildle-text sm:text-4xl md:text-5xl">
            안전하고 쾌적한 산책,
            <br />
            <span className="bg-gradient-to-r from-gildle-accent to-gildle-accent-bright bg-clip-text text-transparent">
              Gildle
            </span>
            이 안내할게.
          </h1>

          <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-gildle-muted sm:mt-5 sm:text-base">
            길+엮다에서 태어난 이름.
            <br />
            나무 그늘, 결빙 위험, 반려견 친화도를 계산해
            <br className="hidden sm:block" />
            최적의 산책 경로를 추천합니다.
          </p>

          <div className="mt-8 flex flex-col items-center gap-3 sm:mt-10 sm:flex-row sm:justify-center">
            <Link
              href="/gildle/map"
              className="inline-flex items-center gap-2 rounded-full border border-gildle-accent/30 bg-gildle-accent-soft px-5 py-2.5 text-sm font-semibold text-gildle-accent transition-colors hover:bg-gildle-accent hover:text-white"
            >
              <MapPin className="h-4 w-4" strokeWidth={1.8} />
              보행 그래프 지도 보기
            </Link>
            <span className="inline-flex items-center gap-2 rounded-full border border-gildle-border bg-gildle-surface/60 px-5 py-2.5 text-sm text-gildle-muted">
              경로 추천 — Coming Soon
            </span>
          </div>
        </section>

        <section className="mt-16 w-full max-w-4xl sm:mt-20">
          <div className="grid gap-4 sm:grid-cols-3 sm:gap-6">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-2xl border border-gildle-border bg-gildle-surface/80 p-5 sm:p-6"
              >
                <f.icon
                  className="mb-3 h-6 w-6 text-gildle-accent"
                  strokeWidth={1.8}
                  aria-hidden
                />
                <h3 className="mb-1.5 text-sm font-semibold text-gildle-text">
                  {f.title}
                </h3>
                <p className="text-xs leading-relaxed text-gildle-muted">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12 w-full max-w-2xl sm:mt-16">
          <h2 className="mb-4 text-center text-xs font-medium tracking-wider text-gildle-muted uppercase sm:mb-5">
            데이터 기반
          </h2>
          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
            {DATA_SOURCES.map((d) => (
              <div
                key={d.label}
                className="flex items-center gap-2 rounded-full border border-gildle-border bg-gildle-surface/60 px-4 py-2"
              >
                <d.icon
                  className="h-4 w-4 text-gildle-accent"
                  strokeWidth={1.8}
                  aria-hidden
                />
                <span className="text-xs text-gildle-text">{d.label}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
