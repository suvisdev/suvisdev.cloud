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
      await refreshMovaRankings(source)
      router.refresh() // 서버 컴포넌트 재실행 → 최신 스냅샷 로드
    } catch {
      // 실패 시 조용히 무시 — 기존 데이터 유지
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleRefresh}
      disabled={loading}
      className="inline-flex items-center gap-1.5 rounded-full border border-[var(--mova-border)] bg-[var(--mova-surface)] px-3 py-1.5 text-xs font-medium text-[var(--mova-muted)] transition-colors hover:text-[var(--mova-text)] disabled:opacity-50"
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
