import type { Metadata } from "next"
import { MovaFooter } from "@/components/mova/mova-footer"
import { MovaHeader } from "@/components/mova/mova-header"
import "./mova.css"

export const metadata: Metadata = {
  title: "Mova — AI Movie Agent",
  description: "취향 기반 영화·시리즈 추천 플랫폼",
  // 상위 레이아웃의 공통 아이콘 대신 Mova 아이콘(2026-10-06). 파일 규칙 icon.svg는 상위 icons 설정을 못 덮어 metadata로 지정
  icons: { icon: "/mova-icon.svg" },
}

export default function MovaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mova-app flex min-h-dvh flex-col">
      {/* 헤더를 레이아웃에 두면 페이지 이동 시 리마운트가 없어 좌상단
          로그인 영역 깜빡임이 사라진다(2026-08-26). /mova/login에서는
          MovaHeader가 스스로 숨는다. */}
      <MovaHeader />
      {children}
      <MovaFooter />
    </div>
  )
}
