export type AppCatalogItem = {
  id: string
  titleKo: string
  titleEn: string
  href?: string
  available: boolean
  /** 홀수(1,3,5): 텍스트 상단 · 짝수(2,4,6): 이미지 상단 */
  imageFirst: boolean
  gradient: string
  /** 팀 프로젝트 소속 팀명 */
  team?: string
  /** 카드 이미지 영역에 표시할 이모지 아이콘 (커버 사진이 없을 때) */
  icon?: string
  /** 카드 이미지 영역에 표시할 커버 사진 (public 경로) */
  image?: string
}

export const APPS_CATALOG: AppCatalogItem[] = [
  {
    id: "mova",
    titleKo: "Mova",
    titleEn: "AI Movie Agent",
    href: "/mova",
    available: true,
    imageFirst: false,
    gradient: "from-zinc-900 via-red-950 to-black",
    image: "/apps-mova.jpg",
  },
  {
    id: "gildle",
    titleKo: "Gildle",
    titleEn: "Dog Walk Guide",
    href: "/gildle",
    available: false,
    imageFirst: true,
    gradient: "from-emerald-400 via-green-500 to-teal-600",
    image: "/apps-gildle.jpg",
  },
]

export const TEAM_PROJECTS: AppCatalogItem[] = [
  {
    id: "yaksok",
    titleKo: "Yaksok",
    titleEn: "알약 식별",
    href: "https://seuk.cloud",
    available: false,
    imageFirst: true,
    gradient: "from-sky-400 via-blue-500 to-cyan-600",
    image: "/apps-yaksok.jpg",
    team: "Team Seuk",
  },
]
