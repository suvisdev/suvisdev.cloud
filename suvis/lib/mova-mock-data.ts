export type MovaNavItem = { label: string; href: string; active?: boolean }

export const MOVA_NAV: MovaNavItem[] = [
  { label: "홈", href: "/mova" },
  { label: "영화", href: "/mova/movies" },
  { label: "컬렉션", href: "/mova/collections" },
  { label: "랭킹", href: "/mova/rankings" },
  { label: "마이", href: "/mova/mypage" },
]

export const MOVA_QUICK_ACTIONS = [
  { id: "magazine", label: "매거진", emoji: "📰" },
  { id: "event", label: "이벤트", emoji: "🎁" },
  { id: "rating", label: "평가", emoji: "⭐" },
  { id: "taste", label: "취향분석", emoji: "🎯" },
  { id: "recommend", label: "추천", emoji: "✨" },
]

