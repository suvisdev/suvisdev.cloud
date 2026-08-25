"use client"

import { useState } from "react"
import { Loader2, MessageCircle, Trash2 } from "lucide-react"
import {
  addReviewComment,
  deleteReviewComment,
  fetchReviewComments,
  type MovaReviewComment,
} from "@/lib/mova-api"
import type { SuvisSession } from "@/lib/suvis-session"

type MovaReviewCommentsProps = {
  reviewId: number
  session: SuvisSession | null
}

/** 리뷰 카드 하단 댓글 스레드 — 접힘 기본, 펼치면 로드. 로그인 시 작성 가능. */
export function MovaReviewComments({ reviewId, session }: MovaReviewCommentsProps) {
  const [open, setOpen] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<MovaReviewComment[]>([])
  const [draft, setDraft] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggle = async () => {
    const next = !open
    setOpen(next)
    if (next && !loaded) {
      setLoading(true)
      const rows = await fetchReviewComments(reviewId)
      setItems(rows)
      setLoaded(true)
      setLoading(false)
    }
  }

  const submit = async () => {
    const text = draft.trim()
    if (!text || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const created = await addReviewComment(reviewId, text)
      setItems((prev) => [...prev, created])
      setDraft("")
    } catch (e) {
      setError(e instanceof Error ? e.message : "댓글 등록에 실패했습니다.")
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (commentId: number) => {
    try {
      await deleteReviewComment(commentId)
      setItems((prev) => prev.filter((c) => c.id !== commentId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "댓글 삭제에 실패했습니다.")
    }
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => void toggle()}
        className="inline-flex items-center gap-1 text-xs text-neutral-500 transition-colors hover:text-mova-text"
      >
        <MessageCircle className="h-3 w-3" />
        댓글{loaded && items.length > 0 ? ` ${items.length}` : ""}
      </button>

      {open ? (
        <div className="mt-2 space-y-2 border-l-2 border-mova-border pl-3">
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-mova-muted" />
          ) : items.length === 0 ? (
            <p className="text-xs text-neutral-500">첫 댓글을 남겨보세요.</p>
          ) : (
            items.map((c) => (
              <div key={c.id} className="group flex items-start justify-between gap-2">
                <p className="min-w-0 text-xs leading-relaxed text-neutral-300">
                  <span className="mr-1.5 font-medium text-mova-text">{c.nickname}</span>
                  {c.body}
                </p>
                {session && session.id === c.user_id ? (
                  <button
                    type="button"
                    onClick={() => void remove(c.id)}
                    aria-label="댓글 삭제"
                    className="shrink-0 text-neutral-600 opacity-0 transition group-hover:opacity-100 hover:text-rose-400"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                ) : null}
              </div>
            ))
          )}

          {session ? (
            <div className="flex items-center gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.nativeEvent.isComposing) void submit()
                }}
                placeholder="댓글 달기..."
                maxLength={500}
                className="h-8 min-w-0 flex-1 rounded-md border border-mova-border bg-mova-surface-2 px-2.5 text-xs text-mova-text outline-none focus:border-mova-accent/60"
              />
              <button
                type="button"
                onClick={() => void submit()}
                disabled={submitting || !draft.trim()}
                className="shrink-0 rounded-md bg-mova-accent px-2.5 py-1.5 text-xs font-medium text-white disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-3 w-3 animate-spin" /> : "등록"}
              </button>
            </div>
          ) : (
            <p className="text-xs text-neutral-500">로그인 후 댓글을 남길 수 있어요.</p>
          )}
          {error ? (
            <p className="text-xs text-rose-400" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
