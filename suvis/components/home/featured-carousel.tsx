"use client"

import { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const SLIDES = [
  {
    title: "Mova",
    subtitle: "AI 영화 추천 에이전트",
    caption: "[MOVA] 취향 기반 맞춤 영화 추천 서비스 OPEN",
    gradient: "from-zinc-900 via-red-950 to-black",
  },
  {
    title: "Cinema",
    subtitle: "Curated for You",
    caption: "[추천] 이번 주 인기 상영작 & 신작 프리뷰",
    gradient: "from-neutral-900 via-amber-950 to-zinc-950",
  },
  {
    title: "Archive",
    subtitle: "Discover Stories",
    caption: "[아카이브] 장르별 클래식 & 단편 컬렉션",
    gradient: "from-slate-900 via-indigo-950 to-black",
  },
  {
    title: "Premiere",
    subtitle: "Opening Soon",
    caption: "[프리미어] 시사회 & 팝업 스크리닝 일정",
    gradient: "from-stone-900 via-rose-950 to-neutral-950",
  },
  {
    title: "Studio",
    subtitle: "Behind the Scene",
    caption: "[스튜디오] 제작 비하인드 & 인터뷰",
    gradient: "from-zinc-950 via-orange-950 to-black",
  },
  {
    title: "Night",
    subtitle: "Late Show",
    caption: "[나이트] 심야 상영 & 특별 프로그램",
    gradient: "from-black via-violet-950 to-zinc-900",
  },
  {
    title: "Family",
    subtitle: "All Ages",
    caption: "[패밀리] 주말 가족 영화 라인업",
    gradient: "from-emerald-950 via-teal-950 to-zinc-950",
  },
] as const

export function FeaturedCarousel() {
  const [index, setIndex] = useState(0)
  const total = SLIDES.length
  const slide = SLIDES[index]

  const prev = () => setIndex((i) => (i - 1 + total) % total)
  const next = () => setIndex((i) => (i + 1) % total)

  return (
    <div className="relative flex h-full min-h-[420px] flex-col lg:min-h-0">
      <div
        className={cn(
          "relative flex flex-1 flex-col justify-end bg-gradient-to-br p-8 md:p-10 lg:p-12",
          slide.gradient,
        )}
      >
        <div className="pointer-events-none absolute inset-0 bg-black/25" aria-hidden />
        <div className="relative z-10 max-w-md space-y-3 text-white">
          <p className="font-serif text-4xl font-light tracking-wide md:text-5xl lg:text-6xl">
            {slide.title}
          </p>
          <p className="text-sm font-light tracking-[0.2em] text-white/80 uppercase md:text-base">
            {slide.subtitle}
          </p>
        </div>
      </div>

      <div className="flex items-stretch border-t border-black/10 bg-white text-neutral-900">
        <div className="flex min-w-[4.5rem] items-center justify-center border-r border-black/10 px-4 py-4 text-sm tabular-nums tracking-widest">
          {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
        </div>
        <div className="flex flex-1 items-center px-4 py-3 text-xs leading-snug md:text-sm">
          {slide.caption}
        </div>
        <div className="flex border-l border-black/10">
          <button
            type="button"
            onClick={prev}
            className="flex h-full w-12 items-center justify-center border-r border-black/10 transition-colors hover:bg-neutral-100"
            aria-label="이전 슬라이드"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={next}
            className="flex h-full w-12 items-center justify-center transition-colors hover:bg-neutral-100"
            aria-label="다음 슬라이드"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
