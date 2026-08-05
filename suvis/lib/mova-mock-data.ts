export type MovaNavItem = { label: string; href: string; active?: boolean }

export const MOVA_NAV: MovaNavItem[] = [
  { label: "홈", href: "/mova" },
  { label: "영화", href: "/mova/movies" },
  { label: "컬렉션", href: "/mova/collections" },
  { label: "랭킹", href: "/mova/rankings" },
  { label: "마이", href: "/mova/mypage" },
]

