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
  /** 홈 원형 타일에만 쓸 그림 — 없으면 image. /apps 카드 커버는 image 그대로 */
  tileImage?: string
  /** 홈 타일 아래 한 줄 — 개인/팀 프로젝트 구분 */
  kind: string
  /** kind 아래 작은 글씨(해커톤 출품작 등). 줄바꿈되면 "해커톤 출품작"은 한 덩어리로 — \u00a0(줄바꿈 없는 공백) */
  note?: string
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
    tileImage: "/mova-icon.svg",
    kind: "개인 프로젝트",
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
    tileImage: "/gildle-icon.svg",
    kind: "개인 프로젝트",
  },
]

export const TEAM_PROJECTS: AppCatalogItem[] = [
  {
    id: "arda",
    titleKo: "ARDA",
    titleEn: "AI Recruitment Assistant",
    href: "https://seuk.suvisdev.cloud",
    available: true,
    imageFirst: false,
    gradient: "from-violet-500 via-purple-600 to-indigo-700",
    image: "/apps-arda.svg",
    tileImage: "/arda-icon.svg",
    team: "Team Seuk",
    kind: "팀 프로젝트",
    note: "원티드 해커톤\u00a0출품작",
  },
  {
    // 08-26 SEUK 카드로 교체됐던 팀 프로젝트 '약속'(알약 식별)을 복원(2026-09-28 사용자 요청).
    id: "yaksok",
    titleKo: "약속",
    titleEn: "알약 식별",
    href: "https://www.seuk.cloud/",
    available: true,
    imageFirst: true,
    gradient: "from-sky-400 via-blue-500 to-cyan-600",
    image: "/apps-yaksok.jpg",
    tileImage: "/yaksok-icon.svg",
    team: "Team Seuk",
    kind: "팀 프로젝트",
    note: "문화체육관광 해커톤\u00a0출품작",
  },
]
