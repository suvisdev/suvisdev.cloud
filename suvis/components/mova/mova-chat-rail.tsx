"use client"

import { useEffect, useState } from "react"
import { MovaRankingSection } from "@/components/mova/mova-ranking-section"
import { fetchHotRankings, type MovaHotRankingItem } from "@/lib/mova-api"

/**
 * 데스크톱(lg+) 우측 레일 — 짧은 랭킹만 노출.
 * 클라이언트 fetch로 가볍게 로드(SSR로 페이지가 무거워지지 않게).
 */
export function MovaChatRail() {
  const [items, setItems] = useState<MovaHotRankingItem[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    void fetchHotRankings(8)
      .then((rows) => {
        if (!cancelled) setItems(rows)
      })
      .catch(() => {
        // 랭킹 실패는 조용히 스킵 — 채팅 자체는 계속 동작해야 한다.
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (!ready || items.length === 0) return null

  return (
    <aside className="hidden w-72 shrink-0 overflow-y-auto border-l border-mova-border bg-mova-surface/60 p-3 lg:block">
      <MovaRankingSection variant="sidebar" items={items} />
    </aside>
  )
}
