"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Sparkles } from "lucide-react"
import { fetchProfile } from "@/lib/profile-api"
import { getSuvisSession } from "@/lib/suvis-session"

/**
 * 홈 화면 개인화 흔적 — 챗 답변 안에서만 조용히 쓰이던 preferred_genres를
 * 화면에도 노출한다. 온보딩 카드(`MovaGenreOnboarding`)와 상호 배타적:
 * 저 카드는 장르가 비어 있을 때만 뜨고, 이 배지는 채워져 있을 때만 뜬다.
 */
export function MovaPreferredGenresBadge() {
  const [genres, setGenres] = useState<string[] | null>(null)

  useEffect(() => {
    const session = getSuvisSession()
    if (!session) return
    fetchProfile(session.id)
      .then((p) => setGenres(p.preferred_genres))
      .catch(() => undefined)
  }, [])

  if (!genres || genres.length === 0) return null

  return (
    <section className="flex flex-wrap items-center gap-2 rounded-xl border border-mova-border bg-mova-surface px-4 py-2.5">
      <Sparkles className="h-3.5 w-3.5 shrink-0 text-mova-accent" />
      <span className="text-xs text-neutral-400">내 취향</span>
      <div className="flex flex-wrap gap-1">
        {genres.map((g) => (
          <span
            key={g}
            className="rounded-full bg-mova-accent-soft px-2.5 py-0.5 text-[11px] font-medium text-mova-accent"
          >
            {g}
          </span>
        ))}
      </div>
      <Link
        href="/mova/mypage"
        className="ml-auto shrink-0 text-[11px] text-neutral-500 underline-offset-2 hover:text-mova-accent hover:underline"
      >
        편집
      </Link>
    </section>
  )
}
