"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { Loader2, RotateCw } from "lucide-react"
import { refreshMovaRankings } from "@/lib/mova-api"

export function RankingsRefreshButton({ source }: { source: string }) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  async function handleRefresh() {
    setLoading(true)
    try {
      // 백엔드 재집계는 chat_trend만 + admin 전용(2026-09-11) — 비로그인/일반
      // 유저는 401이 나지만 아래 finally의 스냅샷 재로드는 그대로 동작한다.
      if (source === "chat_trend") await refreshMovaRankings(source)
    } catch {
      // 실패 시 조용히 무시 — 기존 스냅샷 유지
    } finally {
      router.refresh() // 서버 컴포넌트 재실행 → 최신 스냅샷 로드
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleRefresh}
      disabled={loading}
      className="inline-flex items-center gap-1.5 rounded-full border border-mova-border bg-mova-surface px-3 py-1.5 text-xs font-medium text-mova-muted transition-colors hover:text-mova-text disabled:opacity-50"
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <RotateCw className="h-3.5 w-3.5" />
      )}
      새로고침
    </button>
  )
}
