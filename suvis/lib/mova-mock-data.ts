export type MovaNavItem = { label: string; href: string; active?: boolean }

export const MOVA_NAV: MovaNavItem[] = [
  { label: "홈", href: "/mova" },
  { label: "채팅", href: "/mova/main" },
  { label: "영화", href: "/mova/movies" },
  { label: "개봉예정", href: "/mova/upcoming" },
  { label: "미니게임", href: "/mova/games" },
  { label: "랭킹", href: "/mova/rankings" },
  { label: "마이", href: "/mova/mypage" },
]

