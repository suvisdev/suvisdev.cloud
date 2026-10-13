import { MovaChatShell } from "@/components/mova/mova-chat-shell"

export default function MovaMainPage() {
  return (
    // 채팅 페이지는 "헤더 + 채팅 + 푸터"가 화면에 딱 맞아 바깥 스크롤이 없다(2026-10-07 사용자 요청 — 전엔 푸터가
    // 채팅 아래로 밀려 페이지가 푸터 높이만큼 스크롤됐다). mova-chat-fill 이 있으면 mova.css 가 레이아웃 루트를
    // 100dvh 로 고정하고, 여기는 남은 높이(flex-1)만 차지한다. min-h-0 + overflow-hidden 이 있어야 챗 리스트만
    // 내부 스크롤되고 입력창이 하단에 붙는다(루트가 콘텐츠만큼 자라던 2026-09-28 실측 문제).
    // 푸터는 TMDB 출처 고지가 있어 숨기지 않는다.
    <div className="mova-chat-fill flex min-h-0 flex-1 flex-col overflow-hidden">
      <MovaChatShell />
    </div>
  )
}
