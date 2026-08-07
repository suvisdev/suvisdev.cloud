"use client"

import { useEffect, useState } from "react"
import { Sparkles, X } from "lucide-react"
import { MovaGenrePicker } from "@/components/mova/mova-genre-picker"
import { fetchProfile, updatePreferredGenres } from "@/lib/profile-api"
import { getSuvisSession } from "@/lib/suvis-session"

const DISMISS_KEY = "mova_genre_onboarding_dismissed"

/**
 * 로그인했는데 선호 장르가 비어 있으면 홈에서 한 번 물어보는 온보딩 카드.
 *
 * **가입 폼이 아니라 로그인 후 시점에 붙인 이유**: 실사용자 4명 중 2명이
 * 카카오·구글 OAuth 가입자라 회원가입 폼을 아예 거치지 않는다(2026-08-07 실측).
 * 폼에만 넣으면 그 절반은 영구히 미설정으로 남고, 기존 가입자도 못 채운다.
 * 이 방식은 가입 경로와 무관하게 전원을 커버한다.
 */
export function MovaGenreOnboarding() {
  const [visible, setVisible] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const session = getSuvisSession()
    if (!session) return
    if (window.localStorage.getItem(DISMISS_KEY) === "1") return

    // 조회 실패(네트워크·401)는 조용히 넘긴다 — 온보딩은 부가 기능이라
    // 홈 화면 자체를 막으면 안 된다.
    fetchProfile(session.id)
      .then((p) => {
        if (p.preferred_genres.length === 0) setVisible(true)
      })
      .catch(() => undefined)
  }, [])

  const dismiss = () => {
    window.localStorage.setItem(DISMISS_KEY, "1")
    setVisible(false)
  }

  const handleSave = async () => {
    const session = getSuvisSession()
    if (!session) return
    setSaving(true)
    try {
      await updatePreferredGenres(session.id, selected)
      dismiss()
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장하지 못했습니다.")
    } finally {
      setSaving(false)
    }
  }

  if (!visible) return null

  return (
    <section className="relative rounded-2xl border border-mova-accent/30 bg-mova-surface p-5">
      <button
        type="button"
        onClick={dismiss}
        aria-label="닫기"
        className="absolute top-4 right-4 text-neutral-500 transition hover:text-mova-text"
      >
        <X className="h-4 w-4" />
      </button>

      <div className="mb-1 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-mova-accent" />
        <h2 className="text-sm font-semibold text-mova-text">어떤 영화를 좋아하세요?</h2>
      </div>
      <p className="mb-3 text-xs text-neutral-400">
        고른 장르는 AI 추천에 반영돼요. 나중에 마이페이지에서 바꿀 수 있어요.
      </p>

      <MovaGenrePicker value={selected} onChange={setSelected} />

      {error && <p className="mt-3 text-xs text-rose-400">{error}</p>}

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || selected.length === 0}
          className="rounded-lg bg-mova-accent px-4 py-2 text-xs font-medium text-black transition disabled:opacity-50"
        >
          {saving ? "저장 중…" : "저장하고 시작하기"}
        </button>
        <button
          type="button"
          onClick={dismiss}
          className="rounded-lg border border-mova-border px-4 py-2 text-xs text-neutral-400 transition hover:text-mova-text"
        >
          나중에
        </button>
      </div>
    </section>
  )
}
