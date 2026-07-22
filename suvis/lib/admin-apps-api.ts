export type AppHealth = "정상" | "점검" | "오류"

export type AppInfo = {
  id: string
  name: string
  description: string
  health: AppHealth
  href?: string
}

/** TODO: 앱별 헬스체크 API 연동 전까지 mock. */
export async function listApps(): Promise<AppInfo[]> {
  return [
    { id: "mova", name: "Mova", description: "AI 영화 추천·채팅 에이전트", health: "정상", href: "/mova" },
    { id: "gildle", name: "Gildle", description: "반려견 산책 가이드 (개발중)", health: "점검" },
    { id: "titanic", name: "Titanic", description: "타이타닉 생존 예측 ML 대시보드", health: "정상", href: "/titanic" },
    { id: "doro", name: "Doro", description: "개발 예정", health: "점검" },
    { id: "star_craft", name: "Star Craft", description: "개발 예정", health: "오류" },
  ]
}
