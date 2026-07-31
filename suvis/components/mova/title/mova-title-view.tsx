"use client"

import Link from "next/link"
import Image from "next/image"
import { useEffect, useState } from "react"
import { ArrowLeft, Bookmark, BookmarkCheck, Loader2, Star, ThumbsUp } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import { Button } from "@/components/ui/button"
import { initialFormStatus, patchState, type FormStatus } from "@/lib/form-status"
import {
  addToWatchlist,
  checkWatchlist,
  createMovaReview,
  fetchMovaRating,
  fetchMovaReviewsByMovie,
  movaReviewToComment,
  removeFromWatchlist,
} from "@/lib/mova-api"
import type { MovaComment, MovaMovie } from "@/lib/mova-movies"
import { coercePosterUrl } from "@/lib/mova-poster"
import { getSuvisSession, type SuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type MovaTitleViewProps = {
  movie: MovaMovie
  initialAverageRating: number | null
  initialReviewCount: number | null
}

const CAST_PLACEHOLDER =
  "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&q=80"

function CastAvatar({ name, photo }: { name: string; photo: string }) {
  const src = coercePosterUrl(photo) ?? CAST_PLACEHOLDER
  return (
    <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full bg-neutral-800 md:h-16 md:w-16">
      <Image src={src} alt={name} fill className="object-cover" sizes="64px" />
    </div>
  )
}

function RatingStars({ rating, className }: { rating: number; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1", className)}>
      <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
      <span className="font-medium text-[var(--mova-text)]">{rating.toFixed(1)}</span>
    </span>
  )
}

export function MovaTitleView({
  movie,
  initialAverageRating,
  initialReviewCount,
}: MovaTitleViewProps) {
  const [comments, setComments] = useState<MovaComment[]>(movie.comments)
  const [averageRating, setAverageRating] = useState<number | null>(initialAverageRating)
  const [reviewCount, setReviewCount] = useState<number | null>(initialReviewCount)
  const [session, setSession] = useState<SuvisSession | null>(null)
  const [review, setReview] = useState<FormStatus>(initialFormStatus)
  const [inWatchlist, setInWatchlist] = useState(false)
  const [watchlistLoading, setWatchlistLoading] = useState(false)
  const patchReview = (patch: Partial<FormStatus>) => patchState(setReview, patch)

  const canSubmitReview = Boolean(movie.movieDbId)

  useEffect(() => {
    setComments(movie.comments)
  }, [movie.comments])

  useEffect(() => {
    const s = getSuvisSession()
    setSession(s)
    if (s && movie.movieDbId) {
      checkWatchlist(s.id, movie.movieDbId).then(setInWatchlist).catch(() => null)
    }
  }, [movie.movieDbId])

  const handleWatchlistToggle = async () => {
    if (!session || !movie.movieDbId) return
    setWatchlistLoading(true)
    try {
      if (inWatchlist) {
        await removeFromWatchlist(session.id, movie.movieDbId)
        setInWatchlist(false)
      } else {
        await addToWatchlist(session.id, movie.movieDbId)
        setInWatchlist(true)
      }
    } catch {
      // silent fail
    } finally {
      setWatchlistLoading(false)
    }
  }

  const refreshReviews = async () => {
    if (!movie.movieDbId) return
    const [rows, summary] = await Promise.all([
      fetchMovaReviewsByMovie(movie.movieDbId),
      fetchMovaRating(movie.movieDbId),
    ])
    setComments(rows.map(movaReviewToComment))
    if (summary) {
      setAverageRating(summary.average_rating)
      setReviewCount(summary.review_count)
    }
  }

  const handleReviewSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as {
      rating?: string
      text?: string
    }

    const text = (formProps.text ?? "").trim()
    const rating = Number(formProps.rating)

    const errors: Record<string, string> = {}
    if (!canSubmitReview) {
      errors.text = "이 작품은 API 연동 전이라 리뷰를 남길 수 없습니다."
    }
    if (!session) {
      errors.text = "리뷰를 남기려면 로그인해 주세요."
    }
    if (!text) errors.text = errors.text ?? "리뷰 내용을 입력해 주세요."
    if (!rating || rating < 0.5 || rating > 5) errors.rating = "평점을 선택해 주세요."
    if (Object.keys(errors).length > 0) {
      patchReview({ errors, message: null })
      return
    }
    if (!session || !movie.movieDbId) return

    patchReview({ errors: {}, submitting: true, message: null })
    try {
      await createMovaReview({
        movie_id: movie.movieDbId,
        rating,
        body: text,
      })
      await refreshReviews()
      patchReview({ submitting: false, message: "리뷰가 등록되었습니다." })
      e.currentTarget.reset()
    } catch (err) {
      patchReview({
        submitting: false,
        message: err instanceof Error ? err.message : "리뷰 등록에 실패했습니다.",
      })
    }
  }

  const metaParts = [
    movie.year || null,
    movie.genres.length > 0 ? movie.genres.join(" · ") : null,
    movie.ageRating || null,
    movie.country || null,
  ].filter(Boolean)

  return (
    <>
      <MovaHeader />
      <main className="pb-10">
        <section className="relative min-h-[280px] overflow-hidden md:min-h-[360px]">
          <div className="absolute inset-0 bg-[var(--mova-surface)]">
            <MovaRankingPoster
              src={movie.backdrop}
              alt=""
              sizes="100vw"
              className="object-cover opacity-35 blur-sm scale-105"
            />
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--mova-bg)] via-[var(--mova-bg)]/90 to-[var(--mova-bg)]/40" />
          <div className="absolute inset-0 bg-gradient-to-t from-[var(--mova-bg)] via-transparent to-[var(--mova-bg)]/50" />

          <div className="relative mx-auto max-w-[1400px] px-4 pt-5 md:px-6 md:pt-6">
            <Link
              href="/mova/movies"
              className="inline-flex items-center gap-1.5 text-sm text-neutral-400 transition hover:text-[var(--mova-text)]"
            >
              <ArrowLeft className="h-4 w-4" />
              영화 목록
            </Link>
          </div>

          <div className="relative mx-auto flex max-w-[1400px] flex-col gap-6 px-4 py-6 md:flex-row md:items-end md:gap-10 md:px-6 md:pb-10">
            <div className="relative mx-auto h-[220px] w-[148px] shrink-0 overflow-hidden rounded-lg shadow-[0_12px_40px_rgba(0,0,0,0.35)] md:mx-0 md:h-[280px] md:w-[188px]">
              <MovaRankingPoster
                src={movie.poster}
                alt={movie.title}
                sizes="188px"
                className="object-cover"
              />
            </div>

            <div className="min-w-0 flex-1 pb-1">
              {movie.rankBadge ? (
                <p className="mb-2 text-xs font-medium tracking-wide text-[var(--mova-accent-bright)]">
                  {movie.rankBadge}
                </p>
              ) : null}
              <h1 className="font-display text-2xl font-bold text-[var(--mova-text)] md:text-4xl">
                {movie.title}
              </h1>
              {metaParts.length > 0 ? (
                <p className="mt-2 text-sm text-[var(--mova-muted)]">{metaParts.join(" · ")}</p>
              ) : null}
              <div className="mt-3 flex flex-wrap items-center gap-3">
                {session && movie.movieDbId ? (
                  <button
                    type="button"
                    onClick={() => void handleWatchlistToggle()}
                    disabled={watchlistLoading}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                      inWatchlist
                        ? "border-[var(--mova-accent)] bg-[var(--mova-accent-soft)] text-[var(--mova-accent)]"
                        : "border-[var(--mova-border)] bg-[var(--mova-surface)] text-neutral-400 hover:border-[var(--mova-accent)]/40 hover:text-[var(--mova-text)]",
                      "disabled:opacity-50",
                    )}
                  >
                    {inWatchlist ? (
                      <BookmarkCheck className="h-4 w-4" />
                    ) : (
                      <Bookmark className="h-4 w-4" />
                    )}
                    {inWatchlist ? "찜 완료" : "찜하기"}
                  </button>
                ) : null}
                <RatingStars rating={averageRating ?? movie.rating} />
                {reviewCount !== null ? (
                  <span className="text-xs text-neutral-500">리뷰 {reviewCount.toLocaleString()}개</span>
                ) : movie.ratingCount > 0 ? (
                  <span className="text-xs text-neutral-500">{movie.ratingCount.toLocaleString()}명 평가</span>
                ) : null}
                {movie.platform ? (
                  <span className="rounded-full border border-[var(--mova-border)] bg-[var(--mova-surface)] px-2.5 py-0.5 text-xs capitalize text-neutral-300">
                    {movie.platform}
                  </span>
                ) : null}
                {movie.badge ? (
                  <span className="rounded bg-[var(--mova-accent)] px-2 py-0.5 text-[10px] font-bold text-white">
                    {movie.badge}
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-[1400px] space-y-8 px-4 py-6 md:px-6 md:py-8">
          {movie.synopsis ? (
            <section className="rounded-xl border border-[var(--mova-border)] bg-[var(--mova-surface)] p-4 md:p-5">
              <h2 className="text-base font-semibold text-[var(--mova-text)]">줄거리</h2>
              <p className="mt-3 text-sm leading-relaxed text-neutral-300">{movie.synopsis}</p>
            </section>
          ) : null}

          {movie.cast.length > 0 ? (
            <section>
              <h2 className="mb-3 text-base font-semibold text-[var(--mova-text)]">출연 · 제작</h2>
              <ul className="mova-row-scroll flex gap-4 overflow-x-auto pb-2">
                {movie.cast.map((member) => (
                  <li key={`${member.name}-${member.role}`} className="w-24 shrink-0 text-center md:w-28">
                    <CastAvatar name={member.name} photo={member.photo} />
                    <p className="mt-2 truncate text-sm font-medium text-[var(--mova-text)]">{member.name}</p>
                    <p className="truncate text-xs text-neutral-500">{member.role}</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {movie.gallery.length > 0 ? (
            <section>
              <h2 className="mb-3 text-base font-semibold text-[var(--mova-text)]">스틸컷</h2>
              <ul className="mova-row-scroll flex gap-3 overflow-x-auto pb-2">
                {movie.gallery.map((src) => (
                  <li
                    key={src}
                    className="relative h-28 w-44 shrink-0 overflow-hidden rounded-lg border border-[var(--mova-border)] md:h-36 md:w-56"
                  >
                    <MovaRankingPoster src={src} alt="" sizes="224px" className="object-cover" />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <h2 className="mb-3 text-base font-semibold text-[var(--mova-text)]">리뷰</h2>
              {comments.length === 0 ? (
                <p className="text-sm text-neutral-400">아직 등록된 리뷰가 없습니다.</p>
              ) : (
                <ul className="space-y-3">
                  {comments.map((comment) => (
                    <li
                      key={comment.id}
                      className="rounded-lg border border-[var(--mova-border)] bg-[var(--mova-surface)] p-4"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-[var(--mova-text)]">{comment.user}</p>
                        <RatingStars rating={comment.rating} className="text-xs" />
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-neutral-300">{comment.text}</p>
                      <p className="mt-2 inline-flex items-center gap-1 text-xs text-neutral-500">
                        <ThumbsUp className="h-3 w-3" />
                        {comment.likes}
                        {comment.commentCount > 0 ? ` · 댓글 ${comment.commentCount}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <aside className="h-fit rounded-xl border border-[var(--mova-border)] bg-[var(--mova-surface)] p-4 md:p-5">
              <h2 className="text-base font-semibold text-[var(--mova-text)]">리뷰 남기기</h2>
              {!canSubmitReview ? (
                <p className="mt-3 text-xs text-neutral-500">
                  API에 등록된 작품만 리뷰를 남길 수 있습니다.
                </p>
              ) : !session ? (
                <p className="mt-3 text-xs text-neutral-500">
                  <Link href="/login" className="text-[var(--mova-accent-bright)] hover:underline">
                    로그인
                  </Link>
                  후 리뷰를 남길 수 있습니다.
                </p>
              ) : null}
              <form onSubmit={handleReviewSubmit} className="mt-4 space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-neutral-400" htmlFor="review-rating">
                    평점
                  </label>
                  <select
                    id="review-rating"
                    name="rating"
                    defaultValue=""
                    disabled={!canSubmitReview || review.submitting}
                    className="h-9 w-full rounded-md border border-[var(--mova-border)] bg-[var(--mova-bg)] px-3 text-sm text-[var(--mova-text)]"
                  >
                    <option value="" disabled>
                      선택
                    </option>
                    {[5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5].map((value) => (
                      <option key={value} value={value}>
                        {value}점
                      </option>
                    ))}
                  </select>
                  {review.errors.rating ? (
                    <p className="text-xs text-rose-400" role="alert">
                      {review.errors.rating}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-400" htmlFor="review-text">
                    내용
                  </label>
                  <textarea
                    id="review-text"
                    name="text"
                    rows={4}
                    placeholder="감상을 간단히 남겨 주세요."
                    disabled={!canSubmitReview || review.submitting}
                    className="w-full resize-none rounded-md border border-[var(--mova-border)] bg-[var(--mova-bg)] px-3 py-2 text-sm text-[var(--mova-text)]"
                  />
                  {review.errors.text ? (
                    <p className="text-xs text-rose-400" role="alert">
                      {review.errors.text}
                    </p>
                  ) : null}
                </div>
                <Button type="submit" disabled={!canSubmitReview || review.submitting} className="w-full">
                  {review.submitting ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      등록 중
                    </span>
                  ) : (
                    "리뷰 등록"
                  )}
                </Button>
                {review.message ? (
                  <p className="text-xs text-neutral-300" role="status">
                    {review.message}
                  </p>
                ) : null}
              </form>
            </aside>
          </section>
        </div>
      </main>
    </>
  )
}
