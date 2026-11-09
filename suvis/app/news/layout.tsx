import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "AI 기술 소식 — Suvisdev News",
  description:
    "연구소 블로그·논문·오픈소스 릴리스에서 새 AI 기술과 아키텍처 변화를 모읍니다. 경제 뉴스는 부록.",
  // 상위 레이아웃의 공통 아이콘 대신 뉴스 아이콘 (gildle 레이아웃과 같은 방식)
  icons: { icon: "/news-icon.svg" },
}

export default function NewsLayout({ children }: { children: React.ReactNode }) {
  return <div className="bg-background min-h-screen">{children}</div>
}
