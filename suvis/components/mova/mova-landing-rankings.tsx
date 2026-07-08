"use client"

import { useEffect, useState } from "react"
import { MovaRankingSection } from "@/components/mova/mova-ranking-section"
import { fetchMovaRankings, type MovaHotRankingItem } from "@/lib/mova-api"

export function MovaLandingRankings() {
  const [items, setItems] = useState<MovaHotRankingItem[]>([])

  useEffect(() => {
    fetchMovaRankings("chat_trend").then(setItems).catch(() => {})
  }, [])

  if (!items.length) return null

  return (
    <div className="w-full min-w-0">
      <MovaRankingSection variant="carousel" items={items} title="지금 뜨는 작품" />
    </div>
  )
}
