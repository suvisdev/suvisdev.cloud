"use client"

import Image from "next/image"
import Link from "next/link"
import { useEffect, useState, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import {
  Bookmark,
  Clock,
  Eye,
  Film,
  Loader2,
  LogOut,
  Pencil,
  Search,
  Star,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react"
import { MovaConfirmDialog } from "@/components/mova/mova-confirm-dialog"
import { MovaPosterRow } from "@/components/mova/mova-poster-row"
import { MovaSpoilerBody } from "@/components/mova/mova-spoiler-body"
import {
  deleteMovaAccount,
  deleteMovaReview,
  fetchMovaMypage,
  fetchWatchlist,
  removeFromWatchlist,
  type MypageData,
  type WatchlistItem,
} from "@/lib/mova-api"
import { updateNickname, updatePreferredGenres } from "@/lib/profile-api"
import { MovaGenrePicker } from "@/components/mova/mova-genre-picker"
import { MovaAvatarUploader } from "@/components/mova/mova-avatar-uploader"
import { getSuvisSession, clearSuvisSession, logoutSession } from "@/lib/suvis-session"
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
  const [editingNickname, setEditingNickname] = useState(false)
  const [nicknameDraft, setNicknameDraft] = useState("")
  const [savingNickname, setSavingNickname] = useState(false)
  const [removingMovieId, setRemovingMovieId] = useState<number | null>(null)
  const [removingReviewId, setRemovingReviewId] = useState<number | null>(null)

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
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : "불러오기 실패"
        // 백엔드가 토큰을 거절한 경우(만료·알고리즘 불일치 등) 세션을 조용히
        // 정리하고 로그인 재유도. 에러 문구만 노출하면 사용자가 왜 안 되는지
        // 감을 못 잡는다.
        if (/유효하지 않은 세션|인증이 필요/.test(msg)) {
          clearSuvisSession()
          router.replace("/mova/login?redirect=/mova/mypage")
          return
        }
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [router])

  const handleLogout = () => {
    void logoutSession()
    router.replace("/mova")
  }

  const [deleting, setDeleting] = useState(false)
  // 탈퇴 2단 확인 다이얼로그 단계 — window.confirm/prompt/alert 대체.
  const [accountStep, setAccountStep] = useState<
    "idle" | "confirm" | "input" | "mismatch" | "done"
  >("idle")

  const [accountUsername, setAccountUsername] = useState("")

  const handleDeleteAccount = () => {
    const s = getSuvisSession()
    if (!s) return
    setAccountUsername(s.username)
    setAccountStep("confirm")
  }

  const confirmDeleteAccount = async (typed?: string) => {
    const s = getSuvisSession()
    if (!s) return
    if (typed?.trim() !== s.username) {
      setAccountStep("mismatch")
      return
    }
    setDeleting(true)
    try {
      await deleteMovaAccount(s.id)
      void logoutSession()
      setAccountStep("done")
    } catch (e) {
      setAccountStep("idle")
      setError(e instanceof Error ? e.message : "탈퇴에 실패했습니다.")
      setDeleting(false)
    }
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

  const handleSaveNickname = async () => {
    const s = getSuvisSession()
    const trimmed = nicknameDraft.trim()
    if (!s || !trimmed) return
    setSavingNickname(true)
    try {
      const updated = await updateNickname(s.id, trimmed)
      setData((prev) => (prev ? { ...prev, nickname: updated.nickname } : prev))
      setEditingNickname(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : "닉네임을 변경하지 못했습니다.")
    } finally {
      setSavingNickname(false)
    }
  }

  const handleRemoveFromWatchlist = async (movieId: number) => {
    const s = getSuvisSession()
    if (!s) return
    setRemovingMovieId(movieId)
    try {
      await removeFromWatchlist(s.id, movieId)
      setWatchlist((prev) => prev.filter((item) => item.movie_id !== movieId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "찜을 삭제하지 못했습니다.")
    } finally {
      setRemovingMovieId(null)
    }
  }

  const [pendingReviewId, setPendingReviewId] = useState<number | null>(null)

  const handleDeleteReview = (reviewId: number) => {
    setPendingReviewId(reviewId)
  }

  const confirmDeleteReview = async () => {
    if (pendingReviewId === null) return
    const reviewId = pendingReviewId
    setPendingReviewId(null)
    setRemovingReviewId(reviewId)
    try {
      await deleteMovaReview(reviewId)
      setData((prev) =>
        prev
          ? {
              ...prev,
              my_reviews: prev.my_reviews.filter((r) => r.review_id !== reviewId),
              activity: { ...prev.activity, review_count: prev.activity.review_count - 1 },
            }
          : prev,
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : "리뷰를 삭제하지 못했습니다.")
    } finally {
      setRemovingReviewId(null)
    }
  }

  return (
    <>
      <main className="mx-auto max-w-[900px] space-y-6 px-4 py-5 md:px-6 md:py-8">

        {/* 프로필 헤더 */}
        <section className="flex items-center justify-between gap-4 rounded-2xl border border-mova-border bg-mova-surface p-5">
          <div className="flex items-center gap-4">
            {session && <MovaAvatarUploader userId={session.id} />}
            <div>
              <div className="flex items-center gap-1.5">
                <p className="text-lg font-bold text-mova-text">
                  {data?.nickname ?? session?.username ?? "로딩 중…"}
                </p>
                {data && (
                  <button
                    type="button"
                    onClick={() => {
                      setNicknameDraft(data.nickname ?? "")
                      setEditingNickname(true)
                    }}
                    className="text-neutral-500 transition hover:text-mova-accent"
                    aria-label="닉네임 편집"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
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

        {editingNickname && (
          <section className="rounded-2xl border border-mova-border bg-mova-surface p-5">
            <h2 className="mb-3 text-sm font-semibold text-mova-text">닉네임 편집</h2>
            <input
              type="text"
              value={nicknameDraft}
              onChange={(e) => setNicknameDraft(e.target.value)}
              maxLength={30}
              className="w-full rounded-lg border border-mova-border bg-mova-bg px-3 py-2 text-sm text-mova-text outline-none focus:border-mova-accent/60"
            />
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={handleSaveNickname}
                disabled={savingNickname || nicknameDraft.trim().length === 0}
                className="rounded-lg bg-mova-accent px-4 py-2 text-xs font-medium text-black transition disabled:opacity-50"
              >
                {savingNickname ? "저장 중…" : "저장"}
              </button>
              <button
                type="button"
                onClick={() => setEditingNickname(false)}
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
            <MovaPosterRow
              icon={<Film className="h-4 w-4 text-mova-accent" />}
              title="AI 추천 기록"
              countLabel={`${data.recent_picks.length}편`}
              empty={
                data.recent_picks.length === 0 && (
                  <p className="rounded-xl border border-mova-border bg-mova-surface px-5 py-8 text-center text-sm text-neutral-500">
                    아직 AI 추천을 받은 적이 없어요.{" "}
                    <Link href="/mova/main" className="text-mova-accent underline-offset-2 hover:underline">
                      채팅하러 가기 →
                    </Link>
                  </p>
                )
              }
            >
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
            </MovaPosterRow>

            {/* 찜 목록 */}
            <MovaPosterRow
              icon={<Bookmark className="h-4 w-4 text-mova-accent" />}
              title="찜한 영화"
              countLabel={`${watchlist.length}편`}
              empty={
                watchlist.length === 0 && (
                  <p className="rounded-xl border border-mova-border bg-mova-surface px-5 py-8 text-center text-sm text-neutral-500">
                    찜한 영화가 없어요. 영화 상세 페이지에서 찜하기를 눌러보세요.
                  </p>
                )
              }
            >
              {watchlist.map((item) => {
                const slug = resolveMovaCatalogSlug(item.slug, item.title)
                const poster = coercePosterUrl(item.poster_url) ?? POSTER_PLACEHOLDER
                return (
                  <div key={item.movie_id} className="group w-[100px] shrink-0 md:w-[112px]">
                    <Link href={`/mova/title/${slug}`}>
                      <div className="relative aspect-[2/3] overflow-hidden rounded-lg bg-neutral-900 ring-1 ring-mova-border transition group-hover:ring-mova-accent/50">
                        <Image
                          src={poster}
                          alt={item.title}
                          fill
                          className="object-cover transition duration-300 group-hover:scale-105"
                          sizes="112px"
                        />
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault()
                            handleRemoveFromWatchlist(item.movie_id)
                          }}
                          disabled={removingMovieId === item.movie_id}
                          className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white opacity-0 transition hover:bg-black/80 group-hover:opacity-100 disabled:opacity-50"
                          aria-label={`${item.title} 찜 삭제`}
                        >
                          {removingMovieId === item.movie_id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <X className="h-3 w-3" />
                          )}
                        </button>
                      </div>
                      <p className="mt-1.5 line-clamp-2 text-xs font-medium text-mova-text group-hover:text-mova-accent">
                        {item.title}
                      </p>
                      <p className="mt-0.5 text-[10px] text-neutral-500">{item.release_year}</p>
                    </Link>
                  </div>
                )
              })}
            </MovaPosterRow>

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
                      <li
                        key={review.review_id}
                        className="flex gap-3 rounded-xl border border-mova-border bg-mova-surface p-3 transition hover:border-mova-accent/40"
                      >
                        <Link href={`/mova/title/${slug}`} className="flex min-w-0 flex-1 gap-3">
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
                                <MovaSpoilerBody
                                  body={review.body}
                                  spans={review.spoiler_spans}
                                />
                              </p>
                            )}
                          </div>
                        </Link>
                        <div className="flex shrink-0 flex-col items-end justify-between">
                          <span className="text-[11px] text-neutral-500">
                            {new Date(review.updated_at).toLocaleDateString("ko-KR", {
                              month: "short",
                              day: "numeric",
                            })}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleDeleteReview(review.review_id)}
                            disabled={removingReviewId === review.review_id}
                            className="text-neutral-500 transition hover:text-rose-400 disabled:opacity-50"
                            aria-label="리뷰 삭제"
                          >
                            {removingReviewId === review.review_id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <X className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>
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

            {/* 위험 영역 — 회원 탈퇴 */}
            <section className="rounded-xl border border-red-500/30 bg-red-500/5 p-4 md:p-5">
              <h2 className="text-base font-semibold text-red-400">회원 탈퇴</h2>
              <p className="mt-1 text-xs text-mova-muted">
                탈퇴 시 찜한 영화·리뷰·대화 기록·취향 데이터가 모두 영구 삭제되며 복구할 수 없습니다.
              </p>
              <button
                type="button"
                onClick={() => void handleDeleteAccount()}
                disabled={deleting}
                className="mt-3 rounded-md border border-red-500/50 bg-transparent px-3 py-1.5 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10 disabled:opacity-50"
              >
                {deleting ? "탈퇴 처리 중…" : "계정 탈퇴"}
              </button>
            </section>
          </>
        ) : null}
      </main>
      <MovaConfirmDialog
        open={pendingReviewId !== null}
        title="리뷰 삭제"
        description="이 리뷰를 삭제할까요? 되돌릴 수 없습니다."
        confirmLabel="삭제"
        destructive
        onConfirm={() => void confirmDeleteReview()}
        onClose={() => setPendingReviewId(null)}
      />
      <MovaConfirmDialog
        open={accountStep === "confirm"}
        title="계정 탈퇴"
        description={
          "정말 계정을 탈퇴하시겠습니까?\n찜한 영화·리뷰·대화 기록·취향 데이터가 모두 영구 삭제되며 복구할 수 없습니다."
        }
        confirmLabel="계속"
        destructive
        onConfirm={() => setAccountStep("input")}
        onClose={() => setAccountStep("idle")}
      />
      <MovaConfirmDialog
        open={accountStep === "input"}
        title="아이디 확인"
        description={`계속하려면 아이디 "${accountUsername}"을(를) 입력해 주세요.`}
        confirmLabel={deleting ? "탈퇴 중..." : "탈퇴"}
        destructive
        inputPlaceholder={accountUsername}
        onConfirm={(typed) => void confirmDeleteAccount(typed)}
        onClose={() => setAccountStep("idle")}
      />
      <MovaConfirmDialog
        open={accountStep === "mismatch"}
        title="탈퇴 취소"
        description="아이디가 일치하지 않아 탈퇴가 취소되었습니다."
        cancelLabel={null}
        onConfirm={() => setAccountStep("idle")}
        onClose={() => setAccountStep("idle")}
      />
      <MovaConfirmDialog
        open={accountStep === "done"}
        title="탈퇴 완료"
        description="탈퇴가 완료되었습니다. 그동안 이용해 주셔서 감사합니다."
        cancelLabel={null}
        onConfirm={() => router.replace("/mova")}
        onClose={() => router.replace("/mova")}
      />
    </>
  )
}
