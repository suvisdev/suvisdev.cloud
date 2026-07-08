import type { Metadata } from "next"
import { MovaThemeSetter } from "@/components/mova/mova-theme-setter"
import "./mova.css"

export const metadata: Metadata = {
  title: "Mova — AI Movie Agent",
  description: "취향 기반 영화·시리즈 추천 플랫폼",
}

export default function MovaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mova-app min-h-screen">
      <MovaThemeSetter />
      {children}
    </div>
  )
}
