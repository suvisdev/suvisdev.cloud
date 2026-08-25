"use client"

import Link from "next/link"
import Image from "next/image"
import { useEffect, useState } from "react"
import { Loader2, Star } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { fetchMovaActor, type MovaActorDetail } from "@/lib/mova-api"
import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"
import { coercePosterUrl } from "@/lib/mova-poster"

const CAST_PLACEHOLDER =
  "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&q=80"

type MovaActorDialogProps = {
  actorId: number | null
  onClose: () => void
}

/** 출연·제작 아바타 클릭 시 배우 소개 + 다른 출연작을 보여주는 다이얼로그. */
export function MovaActorDialog({ actorId, onClose }: MovaActorDialogProps) {
  const [actor, setActor] = useState<MovaActorDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (actorId === null) return
    setActor(null)
    setLoading(true)
    let cancelled = false
    fetchMovaActor(actorId).then((detail) => {
      if (cancelled) return
      setActor(detail)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [actorId])

  const films = actor?.filmography ?? []
  const topFilm = films.length
    ? [...films].sort((a, b) => b.rating - a.rating)[0]
    : null
  const intro = actor
    ? `${actor.roleType === "director" ? "감독" : "배우"} ${actor.name} — 등록된 작품 ${films.length}편` +
      (topFilm ? `, 대표작 「${topFilm.title}」${topFilm.year ? ` (${topFilm.year})` : ""}` : "")
    : ""

  return (
    <Dialog open={actorId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[80vh] max-w-lg overflow-y-auto border-mova-border bg-mova-bg text-mova-text">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-mova-muted" />
          </div>
        ) : actor ? (
          <>
            <DialogHeader>
              <div className="flex items-center gap-4">
                <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full bg-neutral-800">
                  <Image
                    src={coercePosterUrl(actor.photo) ?? CAST_PLACEHOLDER}
                    alt={actor.name}
                    fill
                    className="object-cover"
                    sizes="64px"
                  />
                </div>
                <div className="min-w-0 text-left">
                  <DialogTitle className="text-mova-text">{actor.name}</DialogTitle>
                  <p className="mt-1 text-xs text-mova-muted">{intro}</p>
                </div>
              </div>
            </DialogHeader>

            {films.length > 0 ? (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-mova-text">출연 작품</h3>
                <ul className="grid grid-cols-3 gap-3">
                  {films.map((f) => (
                    <li key={f.movieId}>
                      <Link
                        href={`/mova/title/${resolveMovaCatalogSlug(f.slug, f.title)}`}
                        onClick={onClose}
                        className="group block"
                      >
                        <div className="relative aspect-[2/3] overflow-hidden rounded-md bg-neutral-900 ring-1 ring-mova-border transition group-hover:ring-mova-accent/50">
                          {f.poster ? (
                            <Image
                              src={f.poster}
                              alt={f.title}
                              fill
                              className="object-cover transition duration-300 group-hover:scale-105"
                              sizes="150px"
                            />
                          ) : null}
                        </div>
                        <p className="mt-1.5 truncate text-xs font-medium text-mova-text">
                          {f.title}
                        </p>
                        <p className="flex items-center gap-1 text-[11px] text-mova-muted">
                          {f.year}
                          {f.rating > 0 ? (
                            <span className="inline-flex items-center gap-0.5">
                              · <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                              {f.rating.toFixed(1)}
                            </span>
                          ) : null}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="py-4 text-sm text-mova-muted">등록된 출연 작품이 없습니다.</p>
            )}
          </>
        ) : (
          <p className="py-8 text-center text-sm text-mova-muted">
            배우 정보를 불러오지 못했습니다.
          </p>
        )}
      </DialogContent>
    </Dialog>
  )
}
