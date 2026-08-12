import { Play } from "lucide-react"
import { cn } from "@/lib/utils"
import type { NormalizedOttBadge } from "@/lib/mova-ott"

/** 각 OTT 브랜드 컬러의 배지 링크. Play 아이콘 + 사이트명. */
export function MovaOttBadge({ badge }: { badge: NormalizedOttBadge }) {
  return (
    <a
      href={badge.href}
      target="_blank"
      rel="noopener noreferrer"
      title={`${badge.label}에서 검색`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors",
        badge.colors,
      )}
    >
      <Play className="h-3 w-3 fill-current" strokeWidth={0} />
      {badge.label}
    </a>
  )
}
