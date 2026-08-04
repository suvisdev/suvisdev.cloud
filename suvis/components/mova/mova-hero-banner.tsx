import Link from "next/link"
import { Play, Sparkles } from "lucide-react"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import type { MovaHotRankingItem } from "@/lib/mova-api"

type MovaHeroBannerProps = {
  featured?: MovaHotRankingItem | null
}

export function MovaHeroBanner({ featured }: MovaHeroBannerProps) {
  if (!featured) {
    return (
      <section className="relative overflow-hidden rounded-xl border border-mova-border bg-mova-surface px-6 py-14 md:py-20">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_30%_20%,rgba(139,127,212,0.25),transparent_55%)]"
        />
        <p className="relative font-display text-2xl font-bold tracking-tight text-mova-text md:text-4xl">
          취향에 맞는 영화를
          <span className="text-mova-accent-bright"> AI</span>와 함께
        </p>
        <p className="relative mt-3 max-w-lg text-sm text-mova-muted md:text-base">
          장르·분위기·OTT를 말하면 Mova가 오늘 볼 작품을 골라 드려요.
        </p>
      </section>
    )
  }

  return (
    <section className="relative min-h-[320px] overflow-hidden rounded-xl md:min-h-[420px]">
      <div className="absolute inset-0 bg-mova-surface">
        <MovaRankingPoster
          src={featured.poster}
          alt=""
          sizes="100vw"
          className="object-cover opacity-40 blur-sm scale-105"
        />
      </div>
      <div className="absolute inset-0 bg-gradient-to-r from-mova-bg via-mova-bg/85 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-mova-bg via-transparent to-mova-bg/30" />

      <div className="relative mx-auto flex h-full max-w-[1400px] flex-col justify-end gap-6 px-4 py-8 md:flex-row md:items-end md:gap-10 md:px-6 md:py-12">
        <div className="relative mx-auto h-[200px] w-[135px] shrink-0 overflow-hidden rounded-md shadow-[0_8px_24px_rgba(0,0,0,0.18)] dark:shadow-[0_20px_50px_rgba(0,0,0,0.6)] md:mx-0 md:h-[260px] md:w-[175px]">
          <MovaRankingPoster
            src={featured.poster}
            alt={featured.title}
            sizes="175px"
            className="object-cover"
          />
          {featured.rank === 1 && (
            <span className="absolute top-2 left-2 rounded bg-mova-accent px-2 py-0.5 text-[10px] font-bold text-white">
              #1 HOT
            </span>
          )}
        </div>

        <div className="max-w-xl pb-2">
          <p className="mb-2 flex items-center gap-2 text-xs font-medium tracking-wide text-mova-accent-bright uppercase">
            <Sparkles className="h-3.5 w-3.5" />
            오늘의 픽
          </p>
          <h1 className="font-display text-3xl font-bold text-mova-text md:text-5xl">{featured.title}</h1>
          <p className="mt-2 text-sm text-mova-muted md:text-base">
            {featured.year} · ★ {featured.rating}
            {featured.badge ? ` · ${featured.badge}` : ""}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href={`/mova/title/${featured.id}`}
              className="inline-flex items-center gap-2 rounded-md bg-white px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-neutral-200"
            >
              <Play className="h-4 w-4 fill-black" />
              상세 보기
            </Link>
            <Link
              href="/mova/main"
              className="inline-flex items-center gap-2 rounded-md border border-mova-border bg-mova-surface-2 px-5 py-2.5 text-sm font-medium text-mova-text transition hover:bg-mova-surface"
            >
              AI에게 추천 받기
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
