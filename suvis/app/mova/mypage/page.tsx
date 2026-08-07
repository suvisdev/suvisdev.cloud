"use client"

import Image from "next/image"
import Link from "next/link"
import { useEffect, useState, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { Bookmark, Clock, Eye, Film, Loader2, LogOut, Search, Star, ThumbsDown, ThumbsUp, User } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { fetchMovaMypage, fetchWatchlist, type MypageData, type WatchlistItem } from "@/lib/mova-api"
import { updatePreferredGenres } from "@/lib/profile-api"
import { MovaGenrePicker } from "@/components/mova/mova-genre-picker"
import { getSuvisSession, clearSuvisSession } from "@/lib/suvis-session"
import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"
import { coercePosterUrl } from "@/lib/mova-poster"
import { cn } from "@/lib/utils"

const POSTER_PLACEHOLDER =
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80"


function FeedbackBadge({ feedback }: { feedback: string | null }) {
  if (!feedback) return null
  return feedback === "like" ? (
    <span className="inline-flex items-center gap-0.5 rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] text-emerald-400">
      <ThumbsUp className="h-2.5 w-2.5" /> 좋아요
    </span>
  ) : (
    <span className="inline-flex items-center gap-0.5 rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-400">
      <ThumbsDown className="h-2.5 w-2.5" /> 별로
    </span>
  )
}

function StatTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex-1 rounded-xl border border-mova-border bg-mova-surface px-4 py-3 text-center">
      <div className="mb-1 flex items-center justify-center gap-1.5 text-neutral-400">
        {icon}
        <span className="text-[11px]">{label}</span>
      </div>
      <p className="text-lg font-bold text-mova-text">{value}</p>
    </div>
  )
}

export default function MypagePage() {
  const router = useRouter()
  const [data, setData] = useState<MypageData | null>(null)
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingGenres, setEditingGenres] = useState(false)
  const [genreDraft, setGenreDraft] = useState<string[]>([])
  const [savingGenres, setSavingGenres] = useState(false)

  const session = typeof window !== "undefined" ? getSuvisSession() : null

  useEffect(() => {
    const s = getSuvisSession()
    if (!s) {
      router.replace("/mova/login?redirect=/mova/mypage")
      return
    }
    Promise.all([
      fetchMovaMypage(s.id),
      fetchWatchlist(s.id).catch(() => ({ items: [], total: 0 })),
    ])
      .then(([mypage, wl]) => {
        setData(mypage)
        setWatchlist(wl.items)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "불러오기 실패"))
      .finally(() => setLoading(false))
  }, [router])

  const handleLogout = () => {
    clearSuvisSession()
    router.replace("/mova")
  }

  const handleSaveGenres = async () => {
    const s = getSuvisSession()
    if (!s) return
    setSavingGenres(true)
    try {
      const updated = await updatePreferredGenres(s.id, genreDraft)
      setData((prev) => (prev ? { ...prev, preferred_genres: updated.preferred_genres } : prev))
      setEditingGenres(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : "선호 장르를 변경하지 못했습니다.")
    } finally {
      setSavingGenres(false)
    }
  }

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[900px] space-y-6 px-4 py-5 md:px-6 md:py-8">

        {/* 프로필 헤더 */}
        <section className="flex items-center justify-between gap-4 rounded-2xl border border-mova-border bg-mova-surface p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-mova-accent-soft">
              <User className="h-7 w-7 text-mova-accent" />
            </div>
            <div>
              <p className="text-lg font-bold text-mova-text">
                {data?.nickname ?? session?.username ?? "로딩 중…"}
              </p>
              <p className="text-sm text-neutral-400">@{session?.username}</p>
              {data && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1">
                  {data.preferred_genres.map((g) => (
                    <span
                      key={g}
                      className="rounded-full bg-mova-accent-soft px-2.5 py-0.5 text-[11px] font-medium text-mova-accent"
                    >
                      {g}
                    </span>
                  ))}
                  {data.preferred_genres.length === 0 && (
                    <span className="text-[11px] text-neutral-500">선호 장르 미설정</span>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setGenreDraft(data.preferred_genres)
                      setEditingGenres(true)
                    }}
                    className="rounded-full border border-mova-border px-2.5 py-0.5 text-[11px] text-neutral-400 transition hover:border-mova-accent/40 hover:text-mova-accent"
                  >
                    편집
                  </button>
                </div>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg border border-mova-border px-3 py-2 text-xs text-neutral-400 transition hover:border-rose-500/40 hover:text-rose-400"
          >
            <LogOut className="h-3.5 w-3.5" />
            로그아웃
          </button>
        </section>

        {editingGenres && (
          <section className="rounded-2xl border border-mova-border bg-mova-surface p-5">
            <h2 className="mb-3 text-sm font-semibold text-mova-text">
              선호 장르 <span className="text-xs text-neutral-500">AI 추천에 반영돼요</span>
            </h2>
            <MovaGenrePicker value={genreDraft} onChange={setGenreDraft} />
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={handleSaveGenres}
                disabled={savingGenres}
                className="rounded-lg bg-mova-accent px-4 py-2 text-xs font-medium text-black transition disabled:opacity-50"
              >
                {savingGenres ? "저장 중…" : "저장"}
              </button>
              <button
                type="button"
                onClick={() => setEditingGenres(false)}
                className="rounded-lg border border-mova-border px-4 py-2 text-xs text-neutral-400 transition hover:text-mova-text"
              >
                취소
              </button>
            </div>
          </section>
        )}

        {loading ? (
          <div className="flex items-center gap-2 py-10 text-sm text-neutral-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            불러오는 중…
          </div>
        ) : error ? (
          <p className="py-10 text-center text-sm text-rose-400">{error}</p>
        ) : data ? (
          <>
            {/* 활동 요약 */}
            <section className="flex gap-3">
              <StatTile
                icon={<Eye className="h-3.5 w-3.5" />}
                label="본 영화"
                value={`${data.activity.watched_count}편`}
              />
              <StatTile
                icon={<Star className="h-3.5 w-3.5" />}
                label="쓴 리뷰"
                value={`${data.activity.review_count}개`}
              />
              <StatTile
                icon={<Star className="h-3.5 w-3.5" />}
                label="평균 별점"
                value={
                  data.activity.average_rating === null
                    ? "—"
                    : data.activity.average_rating.toFixed(1)
                }
              />
            </section>

            {/* AI 픽 기록 */}
            <section>
              <div className="mb-3 flex items-center gap-2">
                <Film className="h-4 w-4 text-mova-accent" />
                <h2 className="text-sm font-semibold text-mova-text">AI 추천 기록</h2>
                <span className="text-xs text-neutral-500">{data.recent_picks.length}편</span>
              </div>

              {data.recent_picks.length === 0 ? (
                <p className="rounded-xl border border-mova-border bg-mova-surface px-5 py-8 text-center text-sm text-neutral-500">
                  아직 AI 추천을 받은 적이 없어요.{" "}
                  <Link href="/mova/main" className="text-mova-accent underline-offset-2 hover:underline">
                    채팅하러 가기 →
                  </Link>
                </p>
              ) : (
                <div className="mova-row-fade -mx-4 px-4 md:-mx-0 md:px-0">
                  <div className="flex gap-3 overflow-x-auto pb-2 md:gap-4">
                    {data.recent_picks.map((pick) => {
                      const slug = resolveMovaCatalogSlug(pick.slug, pick.title)
                      const poster = coercePosterUrl(pick.poster_url) ?? POSTER_PLACEHOLDER
                      return (
                        <Link
                          key={pick.pick_id}
                          href={`/mova/title/${slug}`}
                          className="group w-[100px] shrink-0 md:w-[112px]"
                        >
                          <div className="relative aspect-[2/3] overflow-hidden rounded-lg bg-neutral-900 ring-1 ring-mova-border transition group-hover:ring-mova-accent/50">
                            <Image
                              src={poster}
                              alt={pick.title}
                              fill
                              className="object-cover transition duration-300 group-hover:scale-105"
                              sizes="112px"
                            />
                          </div>
                          <p className="mt-1.5 line-clamp-2 text-xs font-medium text-mova-text group-hover:text-mova-accent">
                            {pick.title}
                          </p>
                          {pick.hook && (
                            <p className="mt-0.5 line-clamp-2 text-[10px] text-neutral-500">
                              {pick.hook}
                            </p>
                          )}
                          <div className="mt-1">
                            <FeedbackBadge feedback={pick.feedback} />
                          </div>
                        </Link>
                      )
                    })}
                  </div>
                </div>
              )}
            </section>

            {/* 찜 목록 */}
            <section>
              <div className="mb-3 flex items-center gap-2">
                <Bookmark className="h-4 w-4 text-mova-accent" />
                <h2 className="text-sm font-semibold text-mova-text">찜한 영화</h2>
                <span className="text-xs text-neutral-500">{watchlist.length}편</span>
              </div>

              {watchlist.length === 0 ? (
                <p className="rounded-xl border border-mova-border bg-mova-surface px-5 py-8 text-center text-sm text-neutral-500">
                  찜한 영화가 없어요. 영화 상세 페이지에서 찜하기를 눌러보세요.
                </p>
              ) : (
                <div className="mova-row-fade -mx-4 px-4 md:-mx-0 md:px-0">
                  <div className="flex gap-3 overflow-x-auto pb-2 md:gap-4">
                    {watchlist.map((item) => {
                      const slug = resolveMovaCatalogSlug(item.slug, item.title)
                      const poster = coercePosterUrl(item.poster_url) ?? POSTER_PLACEHOLDER
                      return (
                        <Link
                          key={item.movie_id}
                          href={`/mova/title/${slug}`}
                          className="group w-[100px] shrink-0 md:w-[112px]"
                        >
                          <div className="relative aspect-[2/3] overflow-hidden rounded-lg bg-neutral-900 ring-1 ring-mova-border transition group-hover:ring-mova-accent/50">
                            <Image
                              src={poster}
                              alt={item.title}
                              fill
                              className="object-cover transition duration-300 group-hover:scale-105"
                              sizes="112px"
                            />
                          </div>
                          <p className="mt-1.5 line-clamp-2 text-xs font-medium text-mova-text group-hover:text-mova-accent">
                            {item.title}
                          </p>
                          <p className="mt-0.5 text-[10px] text-neutral-500">{item.release_year}</p>
                        </Link>
                      )
                    })}
                  </div>
                </div>
              )}
            </section>

            {/* 내 리뷰 */}
            <section>
              <div className="mb-3 flex items-center gap-2">
                <Star className="h-4 w-4 text-mova-accent" />
                <h2 className="text-sm font-semibold text-mova-text">내 리뷰</h2>
                <span className="text-xs text-neutral-500">{data.my_reviews.length}개</span>
              </div>

              {data.my_reviews.length === 0 ? (
                <p className="rounded-xl border border-mova-border bg-mova-surface px-5 py-8 text-center text-sm text-neutral-500">
                  아직 쓴 리뷰가 없어요. 영화 상세 페이지에서 별점과 감상을 남겨보세요.
                </p>
              ) : (
                <ul className="space-y-2">
                  {data.my_reviews.map((review) => {
                    const slug = resolveMovaCatalogSlug(review.slug, review.title)
                    const poster = coercePosterUrl(review.poster_url) ?? POSTER_PLACEHOLDER
                    return (
                      <li key={review.review_id}>
                        <Link
                          href={`/mova/title/${slug}`}
                          className="flex gap-3 rounded-xl border border-mova-border bg-mova-surface p-3 transition hover:border-mova-accent/40"
                        >
                          <div className="relative h-[72px] w-12 shrink-0 overflow-hidden rounded bg-neutral-900">
                            <Image
                              src={poster}
                              alt={review.title}
                              fill
                              className="object-cover"
                              sizes="48px"
                            />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-mova-text">{review.title}</p>
                            {review.rating !== null && (
                              <p className="mt-0.5 flex items-center gap-1 text-xs text-mova-accent">
                                <Star className="h-3 w-3 fill-current" />
                                {review.rating.toFixed(1)}
                              </p>
                            )}
                            {review.body && (
                              <p className="mt-1 line-clamp-2 text-xs text-neutral-400">
                                {review.body}
                              </p>
                            )}
                          </div>
                          <span className="shrink-0 text-[11px] text-neutral-500">
                            {new Date(review.updated_at).toLocaleDateString("ko-KR", {
                              month: "short",
                              day: "numeric",
                            })}
                          </span>
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              )}
            </section>

            {/* 최근 검색 */}
            <section>
              <div className="mb-3 flex items-center gap-2">
                <Search className="h-4 w-4 text-mova-accent" />
                <h2 className="text-sm font-semibold text-mova-text">최근 검색</h2>
              </div>

              {data.recent_searches.length === 0 ? (
                <p className="rounded-xl border border-mova-border bg-mova-surface px-5 py-8 text-center text-sm text-neutral-500">
                  검색 기록이 없어요.
                </p>
              ) : (
                <ul className="space-y-2">
                  {data.recent_searches.map((s, i) => (
                    <li key={i}>
                      <button
                        type="button"
                        onClick={() =>
                          router.push(`/mova/main?q=${encodeURIComponent(s.refined_query)}`)
                        }
                        className={cn(
                          "flex w-full items-center gap-3 rounded-xl border border-mova-border bg-mova-surface px-4 py-3 text-left transition",
                          "hover:border-mova-accent/40 hover:bg-mova-accent-soft",
                        )}
                      >
                        <Clock className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
                        <span className="flex-1 text-sm text-mova-text">
                          {s.refined_query}
                        </span>
                        <span className="text-xs text-neutral-500">
                          {new Date(s.searched_at).toLocaleDateString("ko-KR", {
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </main>
    </>
  )
}
