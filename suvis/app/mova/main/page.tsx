import { MovaChatShell } from "@/components/mova/mova-chat-shell"

export default function MovaMainPage() {
  return (
    // 높이를 "뷰포트 − 헤더"로 **명시**해야 챗 리스트만 내부 스크롤되고 입력창이 하단에 붙는다.
    // 레이아웃 루트가 min-h-dvh(auto 높이)라 flex-1만으로는 안 묶인다 — 콘텐츠만큼 루트가 자라
    // 입력창이 페이지 밖으로 밀렸다(2026-09-28 Playwright 실측: 루트 1130px > 뷰포트 900px).
    // 헤더 실측: 데스크톱 57px(h-14+border), 모바일 86px(h-12+nav). 푸터는 스크롤 아래로 내려간다.
    <div className="flex h-[calc(100dvh-86px)] min-h-0 flex-col overflow-hidden md:h-[calc(100dvh-57px)]">
      <MovaChatShell />
    </div>
  )
}
