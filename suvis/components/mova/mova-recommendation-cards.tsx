"use client"

import Image from "next/image"
import Link from "next/link"
import { useEffect, useState } from "react"
import { Bookmark, BookmarkCheck, Clapperboard } from "lucide-react"
import { DragScrollRow } from "@/components/mova/drag-scroll-row"
import { MovaPlatformBadge } from "@/components/mova/mova-platform-badge"
import {
  addReviewActivity,
  addToWatchlist,
  checkWatchlist,
  removeFromWatchlist,
} from "@/lib/mova-api"
import { getSuvisSession } from "@/lib/suvis-session"
import { coercePosterUrl } from "@/lib/mova-poster"
import { cn } from "@/lib/utils"

export type MovaRecommendation = {
  id: string
  movieDbId?: number | null
  title: string
  year: string
  poster: string
  synopsis: string
  platform?: string | null
  hook: string
}

function WatchlistButton({ userId, movieId }: { userId: number; movieId: number }) {
  const [inWatchlist, setInWatchlist] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    checkWatchlist(userId, movieId).then(setInWatchlist).catch(() => null)
  }, [userId, movieId])

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (inWatchlist) {
        await removeFromWatchlist(userId, movieId)
        setInWatchlist(false)
      } else {
        await addToWatchlist(userId, movieId)
        setInWatchlist(true)
      }
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={(e) => void toggle(e)}
      disabled={loading}
      aria-label={inWatchlist ? "찜 해제" : "찜하기"}
      className={cn(
        "absolute top-1.5 right-1.5 flex h-7 w-7 items-center justify-center rounded-full transition",
        inWatchlist
          ? "bg-mova-accent text-white"
          : "bg-black/50 text-white hover:bg-mova-accent",
        "disabled:opacity-50",
      )}
    >
      {inWatchlist ? (
        <BookmarkCheck className="h-3.5 w-3.5" />
      ) : (
        <Bookmark className="h-3.5 w-3.5" />
      )}
    </button>
  )
}

export function MovaRecommendationCards({ items }: { items: MovaRecommendation[] }) {
  const [userId, setUserId] = useState<number | null>(null)

  useEffect(() => {
    const s = getSuvisSession()
    setUserId(s?.id ?? null)
  }, [])

  if (!items.length) return null

  return (
    <DragScrollRow className="mova-row-scroll flex w-full max-w-full cursor-grab gap-2 overflow-x-auto pb-1">
      {items.map((item) => {
        const posterSrc = coercePosterUrl(item.poster)
        const platformKey = item.platform?.toLowerCase().includes("netflix")
          ? "netflix"
          : item.platform?.toLowerCase().includes("disney")
            ? "disney"
            : item.platform

        const cardContent = (
          <>
            <div className="relative aspect-[2/3] bg-mova-surface-2">
              {posterSrc ? (
                <Image
                  src={posterSrc}
                  alt={item.title ? `${item.title} 포스터` : ""}
                  fill
                  className="object-cover"
                  sizes="200px"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center" aria-hidden>
                  <Clapperboard className="h-8 w-8 text-mova-muted" />
                </div>
              )}
              {userId && item.movieDbId ? (
                <WatchlistButton userId={userId} movieId={item.movieDbId} />
              ) : null}
              {!item.movieDbId && (
                <span className="absolute bottom-1.5 left-1.5 rounded bg-black/60 px-1.5 py-0.5 text-[9px] text-neutral-400">
                  미수록
                </span>
              )}
            </div>
            <div className="p-2.5">
              <div className="flex items-start justify-between gap-1">
                <p className="line-clamp-1 text-sm font-semibold text-mova-text">{item.title}</p>
                {platformKey && <MovaPlatformBadge platform={platformKey} />}
              </div>
              <p className="text-[10px] text-neutral-500">{item.year}</p>
              <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-mova-muted">
                {item.synopsis}
              </p>
              {item.hook && (
                <p className="mt-1 line-clamp-1 text-[10px] text-mova-accent-bright">
                  {item.hook}
                </p>
              )}
            </div>
          </>
        )

        const cardClass = "w-[200px] shrink-0 overflow-hidden rounded-lg border border-mova-border bg-mova-surface"

        return item.movieDbId ? (
          <Link
            key={item.id}
            href={`/mova/title/${item.id}`}
            onClick={() => {
              // 채팅 카드 클릭 기록(로그인만, 2026-08-13). mova 랭킹은 2026-10-07부터 이 클릭이 아니라
              // 상세 화면 열람(비로그인 포함, recordMovieView)으로 센다 — 카드를 누르면 상세가 열려 함께 잡힌다.
              if (item.movieDbId && getSuvisSession()) {
                void addReviewActivity({
                  movie_id: item.movieDbId,
                  action_type: "click",
                }).catch(() => {})
              }
            }}
            className={cn(cardClass, "transition hover:border-mova-accent/40 hover:bg-mova-surface-2")}
          >
            {cardContent}
          </Link>
        ) : (
          <div key={item.id} className={cn(cardClass, "opacity-75")}>
            {cardContent}
          </div>
        )
      })}
    </DragScrollRow>
  )
}
